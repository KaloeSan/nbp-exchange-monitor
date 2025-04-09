from fastapi import FastAPI, Depends, HTTPException, Query, Response, status, File, UploadFile
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.wsgi import WSGIMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from contextlib import asynccontextmanager
from datetime import date, timedelta
from typing import List, Dict, Literal, Union
import logging
import threading
from wsgiref.simple_server import make_server
import uvicorn
from .services.soap.soap_service import wsgi_app, run_server
from . import crud, models, schemas, database
from .config import settings
from .services import nbp_api, notification_service
from . import auth
from lxml import etree
import json
import yaml
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def start_soap_server():
    """Start SOAP server in a separate thread"""
    try:
        soap_thread = threading.Thread(
            target=run_server,
            args=(settings.SOAP_SERVICE_HOST, settings.SOAP_SERVICE_PORT),
            daemon=True
        )
        soap_thread.start()
        logger.info(f"SOAP server started in background thread on port {settings.SOAP_SERVICE_PORT}")
    except Exception as e:
        logger.error(f"Failed to start SOAP server: {e}")
        raise

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events"""
    logger.info("Starting application...")
    try:
        init_db()
        notification_service.start_scheduler(database.get_db)
        start_soap_server()
        yield
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise
    finally:
        logger.info("Shutting down...")
        notification_service.stop_scheduler()

# Initialize FastAPI app with CORS and SOAP support
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount SOAP service
soap_app = WSGIMiddleware(wsgi_app)
app.mount("/soap", soap_app)
logger.info("SOAP service mounted at /soap endpoint")

# --- Database Initialization ---
def init_db():
    try:
        logger.info("Attempting to create database tables...")
        models.Base.metadata.create_all(bind=database.engine)
        logger.info("Database tables checked/created.")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise

# --- API Endpoints ---
@app.get("/", tags=["Health Check"])
def read_root():
    return {"message": f"Welcome to the {settings.PROJECT_NAME}"}

@app.get(f"{settings.API_V1_STR}/currencies", response_model=List[Dict[str, str]], tags=["Data"])
def get_available_currencies():
    return settings.AVAILABLE_CURRENCIES

@app.get(
    f"{settings.API_V1_STR}/data/{{data_type}}",
    response_model=List[Union[schemas.CurrencyExportData, schemas.GoldExportData]],
    tags=["Data"]
)
def get_historical_data(
    data_type: Literal["currency", "gold"],
    start_date: date = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: date = Query(..., description="End date in YYYY-MM-DD format"),
    currencies: str = Query(None, description="Comma-separated list of currency codes (e.g., EUR,USD). Required if data_type is 'currency'")
):
    """
    Fetches historical exchange rates for selected currencies or gold prices
    within a specified date range from the NBP API.

    - **data_type**: Specify 'currency' or 'gold'.
    - **start_date**: The beginning of the date range.
    - **end_date**: The end of the date range.
    - **currencies**: Required only for `data_type=currency`. Provide a comma-separated string of 3-letter currency codes (e.g., "EUR,USD,CHF").
    """
    all_formatted_data = []
    try: 
        if data_type == "currency":
            if not currencies:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Currencies query parameter is required for data_type 'currency'")
            currency_list = [c.strip().upper() for c in currencies.split(',') if c.strip()]
            if not currency_list:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid currencies provided in the 'currencies' parameter.")

            for currency_code in currency_list:
                if not any(c['value'] == currency_code.lower() for c in settings.AVAILABLE_CURRENCIES):
                    logger.warning(f"Requested currency '{currency_code}' not in configured available list.")
                    # raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Currency code '{currency_code}' is not supported.")
                    continue # Ignore unsupported currencies

                rates = nbp_api.get_currency_data_for_range(currency_code, start_date, end_date)
                if rates:
                    all_formatted_data.extend(nbp_api.format_currency_data(rates, currency_code))
                else:
                    logger.warning(f"No data returned from NBP for {currency_code} between {start_date} and {end_date}")

        elif data_type == "gold":
            prices = nbp_api.get_gold_data_for_range(start_date, end_date)
            if prices:
                all_formatted_data.extend(nbp_api.format_gold_data(prices))
            else:
                logger.warning(f"No gold data returned from NBP between {start_date} and {end_date}")

        else: # Invalid data_type
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid data_type.")

        if not all_formatted_data:
            logger.info(f"No data found for request: type={data_type}, start={start_date}, end={end_date}, curr={currencies}")

        all_formatted_data.sort(key=lambda x: x['Date'])
        return all_formatted_data

    except HTTPException as http_exc:
         raise http_exc # Forward HTTP exceptions as is
    except Exception as e:
        logger.error(f"Unexpected error in get_historical_data: {e}", exc_info=True)
        # Zwróć ogólny błąd serwera, jeśli coś innego pójdzie nie tak
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An internal error occurred while fetching data.")
    
@app.post(f"{settings.API_V1_STR}/token", response_model=auth.Token, tags=["Authentication"])
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Logowanie użytkownika przy użyciu nazwy użytkownika i hasła (w form-data).
    Zwraca token JWT przy poprawnym uwierzytelnieniu.

    Użyj np. `testuser` / `testpassword` lub `admin` / `adminpass`.
    """
    user = auth.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Set token lifetime
    access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    # Create a JWT token by encoding the username in the 'sub' (subject) field
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    # Return token in standard OAuth2 format
    return {"access_token": access_token, "token_type": "bearer"}

# Endpoint to create a notification
@app.post(
    f"{settings.API_V1_STR}/notifications",
    response_model=schemas.NotificationRead,
    status_code=status.HTTP_201_CREATED,
    tags=["Notifications"]
)
def add_notification_alert(
    notification: schemas.NotificationCreate,
    db: Session = Depends(database.get_db),
    current_user: auth.UserInDB = Depends(auth.get_current_active_user)  # This ensures authentication
):
    """Creates a new notification alert. Requires authentication."""
    try:
        # Validate currency
        if not any(c['value'] == notification.currency.lower() for c in settings.AVAILABLE_CURRENCIES):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Currency code '{notification.currency}' is not supported."
            )

        # Create notification
        created_notification = crud.create_notification(db=db, notification=notification)
        
        # Immediate check
        notification_service.check_and_notify(created_notification, db)
        
        return created_notification
    except Exception as e:
        logger.error(f"Error creating notification: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.post(f"{settings.API_V1_STR}/import/xml", tags=["Import"])
async def import_data_xml(file: UploadFile = File(...)):
    """
    Imports data from an uploaded XML file.
    Supports the format exported by the application:
    <Data type="currency" startDate="..." endDate="..." currencies="...">
        <CurrencyRate>
            <Date>2025-03-05</Date>
            <Rate>4.1545</Rate>
            <Currency>EUR</Currency>
        </CurrencyRate>
        ...
    </Data>
    """
    try:
        content = await file.read()
        # Parse XML using DOM
        root = etree.fromstring(content)
        
        # Initialize data list
        data = []
        
        # Check if this is our exported format
        if root.tag == 'Data':
            # Parse CurrencyRate elements
            for record in root.findall("CurrencyRate"):
                data.append({
                    "Date": record.find("Date").text,
                    "Value": float(record.find("Rate").text),
                    "Currency": record.find("Currency").text
                })
        else:
            # Fallback for simple format
            for record in root.findall("Record"):
                data.append({
                    "Date": record.find("Date").text,
                    "Value": float(record.find("Value").text)
                })

        # Sort data by date
        sorted_data = sorted(data, key=lambda x: x["Date"])
        
        return {
            "message": "Data imported successfully", 
            "data": sorted_data
        }
    except Exception as e:
        logger.error(f"Error importing XML: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid XML file: {str(e)}")

@app.post(f"{settings.API_V1_STR}/import/json", tags=["Import"])
async def import_data_json(file: UploadFile = File(...)):
    try:
        content = await file.read()
        data = json.loads(content.decode('utf-8'))
        
        formatted_data = []
        records = data.get('data', data) if isinstance(data, dict) else data
        
        if not isinstance(records, list):
            raise HTTPException(status_code=400, detail="Invalid JSON format - expected array of records")
            
        for record in records:
            formatted_data.append({
                "Date": record.get("Date") or record.get("date"),
                "Value": float(record.get("Rate") or record.get("rate") or record.get("Value") or record.get("value")),
                "Currency": record.get("Currency") or record.get("currency", "Unknown")
            })
            
        return {
            "message": "Data imported successfully",
            "data": sorted(formatted_data, key=lambda x: x["Date"])
        }
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON file: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error importing JSON: {str(e)}")

@app.post(f"{settings.API_V1_STR}/import/yaml", tags=["Import"])
async def import_data_yaml(file: UploadFile = File(...)):
    """Imports data from an uploaded YAML file."""
    try:
        content = await file.read()
        data = yaml.safe_load(content)
        
        formatted_data = []
        
        # Handle nested data structure
        records = data.get('Data', data) if isinstance(data, dict) else data
        
        if not isinstance(records, list):
            raise HTTPException(
                status_code=400, 
                detail="Invalid YAML format - expected array of records"
            )
            
        for record in records:
            if not isinstance(record, dict):
                continue
                
            # Ensure currency information is preserved
            formatted_record = {
                "Date": record.get("Date"),
                "Value": float(record.get("Rate", 0) or record.get("Value", 0)),
                "Currency": record.get("Currency", "Unknown").upper()
            }
            
            if not formatted_record["Date"] or formatted_record["Value"] == 0:
                continue
                
            formatted_data.append(formatted_record)
            
        if not formatted_data:
            raise HTTPException(
                status_code=400,
                detail="No valid records found in YAML file"
            )
            
        return {
            "message": "Data imported successfully",
            "data": sorted(formatted_data, key=lambda x: x["Date"])
        }
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML file: {str(e)}")
    except Exception as e:
        logger.error(f"Error importing YAML: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error importing YAML: {str(e)}")

# Endpoint to get all notifications (consider adding authentication/authorization)
@app.get(f"{settings.API_V1_STR}/notifications", response_model=List[schemas.NotificationRead], tags=["Notifications"])
def list_notifications(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(database.get_db)
):
    """
    Retrieves a list of all configured notification alerts.
    (Should ideally be protected).
    """
    notifications = crud.get_notifications(db, skip=skip, limit=limit)
    return notifications

# --- Data Export Endpoints ---
def _generate_export_data(data_type: str, start_date: date, end_date: date, currencies: str | None):
    """Helper to fetch and format data for export, with error handling."""
    try:
        # Reuse the main data fetching logic
        data_models = get_historical_data( # list of dictionaries
            data_type=data_type,
            start_date=start_date,
            end_date=end_date,
            currencies=currencies
        )
        # Make sure data_models is a list, even if it's empty
        if not isinstance(data_models, list):
            logger.error(f"get_historical_data did not return a list, got: {type(data_models)}")
            return []
        return data_models # Return list of dictionaries

    except Exception as e:
        # Catch errors with get_historical_data
        logger.error(f"Error generating export data: {e}", exc_info=True)
        # Throw the exception further so the endpoint can catch it and return 500
        raise

@app.get(f"{settings.API_V1_STR}/export/json", tags=["Export"])
async def export_data_json(
    data_type: Literal["currency", "gold"] = Query(...),
    start_date: date = Query(...),
    end_date: date = Query(...),
    currencies: str = Query(None)
):
    """Exports the selected data in JSON format."""
    try:
        data_list = _generate_export_data(data_type, start_date, end_date, currencies)
        if not data_list:
            # Return 204 No Content if there is no data to export
            return Response(status_code=status.HTTP_204_NO_CONTENT)

        def date_converter(o):
            if isinstance(o, date):
                return o.isoformat()
            raise TypeError(f"Object of type {o.__class__.__name__} is not JSON serializable")

        json_content = json.dumps(data_list, default=date_converter, indent=2)
        filename = f"{data_type}_data_{start_date}_to_{end_date}.json"
        headers = {'Content-Disposition': f'attachment; filename="{filename}"'}
        return Response(content=json_content, media_type="application/json", headers=headers)
    except Exception as e:
        # Log error and return 500 Internal Server Error 
        logger.error(f"Error in export_data_json: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to export data as JSON: {e}")


@app.get(f"{settings.API_V1_STR}/export/xml", tags=["Export"])
async def export_data_xml(
    data_type: Literal["currency", "gold"] = Query(...),
    start_date: date = Query(...),
    end_date: date = Query(...),
    currencies: str = Query(None)
):
    """Exports the selected data in XML format."""
    try: 
        data_list = _generate_export_data(data_type, start_date, end_date, currencies)
        if not data_list:
            return Response(status_code=status.HTTP_204_NO_CONTENT)

        root = etree.Element("Data", type=data_type, startDate=start_date.isoformat(), endDate=end_date.isoformat())
        if data_type == "currency" and currencies:
            root.set("currencies", currencies)

        record_name = "CurrencyRate" if data_type == "currency" else "GoldPrice"

        for entry in data_list:
            item = etree.SubElement(root, record_name)
            for key, value in entry.items():
                text_value = str(value.isoformat() if isinstance(value, date) else value)
                etree.SubElement(item, key).text = text_value

        xml_content = etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8')
        filename = f"{data_type}_data_{start_date}_to_{end_date}.xml"
        headers = {'Content-Disposition': f'attachment; filename="{filename}"'}
        return Response(content=xml_content, media_type="application/xml", headers=headers)
    except Exception as e:
        logger.error(f"Error in export_data_xml: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to export data as XML: {e}")

@app.get(f"{settings.API_V1_STR}/export/yaml", tags=["Export"])
async def export_data_yaml(
    data_type: Literal["currency", "gold"] = Query(...),
    start_date: date = Query(...),
    end_date: date = Query(...),
    currencies: str = Query(None)
):
    """Exports the selected data in YAML format."""
    try:
        data_list = _generate_export_data(data_type, start_date, end_date, currencies)
        if not data_list:
            return Response(status_code=status.HTTP_204_NO_CONTENT)

        data_list_yaml_safe = []
        for item in data_list:
            yaml_item = {}
            for k, v in item.items():
                yaml_item[k] = v.isoformat() if isinstance(v, date) else v
            data_list_yaml_safe.append(yaml_item)

        yaml_content = yaml.dump({"Data": data_list_yaml_safe}, allow_unicode=True, default_flow_style=False)
        filename = f"{data_type}_data_{start_date}_to_{end_date}.yaml"
        headers = {'Content-Disposition': f'attachment; filename="{filename}"'}
        return Response(content=yaml_content, media_type="application/x-yaml", headers=headers)
    except Exception as e:
        logger.error(f"Error in export_data_yaml: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to export data as YAML: {e}")

# Optional: Add health check endpoint for the database
@app.get(f"{settings.API_V1_STR}/health/db", tags=["Health Check"])
def health_check_db(db: Session = Depends(database.get_db)):
    try:
        # Perform a simple query
        db.execute(text("SELECT 1"))
        return {"status": "OK", "message": "Database connection successful"}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection error: {e}",
        )
       
@app.get("/health/soap", tags=["Health Check"])
async def check_soap_health():
    """Check if SOAP service is running"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://{settings.SOAP_SERVICE_HOST}:{settings.SOAP_SERVICE_PORT}/soap?wsdl")
            if response.status_code == 200:
                return {"status": "ok", "message": "SOAP service is running"}
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"SOAP service is not available: {str(e)}"
        )
        
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )