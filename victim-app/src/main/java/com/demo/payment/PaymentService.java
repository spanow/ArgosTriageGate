package com.demo.payment;

import com.demo.order.OrderService;
import com.demo.order.ShopOrder;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClientException;
import org.springframework.web.server.ResponseStatusException;

@Service
public class PaymentService {

    private static final Logger log = LoggerFactory.getLogger(PaymentService.class);

    private final PaymentGatewayClient gateway;
    private final OrderService orders;

    public PaymentService(PaymentGatewayClient gateway, OrderService orders) {
        this.gateway = gateway;
        this.orders = orders;
    }

    /** Les erreurs du prestataire sont journalisées ici (avec la stack trace), puis traduites en 502. */
    public String pay(Long orderId, String mode) {
        ShopOrder order = orders.find(orderId);
        long start = System.currentTimeMillis();
        try {
            String result = "backup".equals(mode)
                    ? gateway.chargeOnBackup(orderId, order.getAmount())
                    : gateway.charge(orderId, order.getAmount(), mode);
            long elapsed = System.currentTimeMillis() - start;
            if (elapsed > 500) {
                log.warn("Payment gateway slow response: {} ms for order {}", elapsed, orderId);
            }
            orders.markPaid(orderId);
            log.info("Payment accepted for order {}", orderId);
            return result;
        } catch (RestClientException e) {
            log.error("Payment failed for order {}", orderId, e);
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "payment failed");
        }
    }
}
