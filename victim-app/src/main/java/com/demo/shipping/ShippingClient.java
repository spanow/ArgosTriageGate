package com.demo.shipping;

import java.math.BigDecimal;
import org.springframework.core.env.Environment;
import org.springframework.stereotype.Component;

@Component
public class ShippingClient {

    private final Environment environment;

    public ShippingClient(Environment environment) {
        this.environment = environment;
    }

    /** Scénario « propriété de config manquante » : la clé du transporteur n'est pas définie, vraie IllegalStateException. */
    public BigDecimal quote(Long orderId) {
        String apiKey = environment.getRequiredProperty("shipping.partner.api-key");
        return new BigDecimal(apiKey.length());
    }
}
