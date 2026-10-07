package com.demo.payment;

import java.math.BigDecimal;
import java.time.Duration;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

/** Client HTTP du prestataire de paiement : les erreurs réseau sont réelles (timeout, connexion refusée, 503). */
@Component
public class PaymentGatewayClient {

    private final RestClient restClient;
    private final String gatewayUrl;
    private final String backupUrl;

    public PaymentGatewayClient(@Value("${payment.gateway.url}") String gatewayUrl,
                                @Value("${payment.gateway.backup-url}") String backupUrl,
                                @Value("${payment.gateway.read-timeout-ms}") long readTimeoutMs) {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(Duration.ofMillis(500));
        factory.setReadTimeout(Duration.ofMillis(readTimeoutMs));
        this.restClient = RestClient.builder().requestFactory(factory).build();
        this.gatewayUrl = gatewayUrl;
        this.backupUrl = backupUrl;
    }

    /** `simulate` est transmis au gateway factice : « slow » (dépasse le timeout), « unavailable » (503). */
    public String charge(Long orderId, BigDecimal amount, String simulate) {
        return restClient.post()
                .uri(gatewayUrl + "/charge?orderId={id}&simulate={simulate}", orderId, simulate)
                .body(amount)
                .retrieve()
                .body(String.class);
    }

    /** Le gateway de secours n'écoute sur aucun port : connexion refusée. */
    public String chargeOnBackup(Long orderId, BigDecimal amount) {
        return restClient.post()
                .uri(backupUrl + "?orderId={id}", orderId)
                .body(amount)
                .retrieve()
                .body(String.class);
    }
}
