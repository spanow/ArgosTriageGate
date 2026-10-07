package com.demo.fraud;

import java.security.cert.CertificateExpiredException;
import javax.net.ssl.SSLHandshakeException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.ResourceAccessException;

/**
 * Client du service anti-fraude (HTTPS chez un partenaire).
 *
 * <p>Scénario « certificat TLS expiré » : SIMULÉ. Monter une vraie PKI expirée hors ligne serait disproportionné ;
 * on lève donc la même chaîne d'exceptions que le JDK et RestClient (ResourceAccessException
 * ← SSLHandshakeException ← CertificateExpiredException), avec des messages réalistes.
 */
@Component
public class FraudCheckClient {

    private static final Logger log = LoggerFactory.getLogger(FraudCheckClient.class);

    private static final String PARTNER_URL = "https://risk.partner-fraudshield.example/v2/score";

    public boolean isSuspicious(Long orderId, boolean partnerCertificateExpired) {
        if (partnerCertificateExpired) {
            CertificateExpiredException expired =
                    new CertificateExpiredException("NotAfter: Sat Oct 03 23:59:59 CEST 2026");
            SSLHandshakeException handshake = new SSLHandshakeException(
                    "PKIX path validation failed: java.security.cert.CertPathValidatorException: validity check failed");
            handshake.initCause(expired);
            throw new ResourceAccessException(
                    "I/O error on POST request for \"" + PARTNER_URL + "\": " + handshake.getMessage(), handshake);
        }
        log.debug("Fraud score requested for order {}", orderId);
        return false;
    }
}
