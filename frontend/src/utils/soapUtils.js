/**
 * Parses SOAP fault messages into human-readable strings.
 * @param {Element|string} fault - The SOAP fault element or XML string.
 * @returns {string} - The parsed fault message.
 */
export function parseSoapFault(fault) {
    try {
        if (typeof fault === 'string') {
            const parser = new DOMParser();
            const xmlDoc = parser.parseFromString(fault, 'text/xml');
            fault = xmlDoc.getElementsByTagName('soap:Fault')[0] || 
                    xmlDoc.getElementsByTagName('Fault')[0];
        }

        if (!fault) return 'Unknown SOAP fault';

        const faultString = fault.getElementsByTagName('faultstring')[0]?.textContent ||
                            fault.textContent;

        return faultString || 'Unknown SOAP fault';
    } catch (error) {
        console.error('Error parsing SOAP fault:', error);
        return 'Failed to parse SOAP fault';
    }
}