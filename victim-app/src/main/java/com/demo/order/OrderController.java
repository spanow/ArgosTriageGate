package com.demo.order;

import com.demo.fraud.FraudCheckClient;
import com.demo.notification.NotificationService;
import com.demo.payment.PaymentService;
import com.demo.shipping.ShippingClient;
import java.math.BigDecimal;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.RestClientException;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/orders")
public class OrderController {

    private static final Logger log = LoggerFactory.getLogger(OrderController.class);

    private final OrderService orders;
    private final PaymentService payments;
    private final ShippingClient shipping;
    private final FraudCheckClient fraud;
    private final NotificationService notifications;

    public OrderController(OrderService orders, PaymentService payments, ShippingClient shipping,
                           FraudCheckClient fraud, NotificationService notifications) {
        this.orders = orders;
        this.payments = payments;
        this.shipping = shipping;
        this.fraud = fraud;
        this.notifications = notifications;
    }

    public record NewOrder(Long customerId, BigDecimal amount, String promoCode) {
    }

    @PostMapping
    public Map<String, Object> create(@RequestBody NewOrder body) {
        ShopOrder order = orders.create(body.customerId(), body.amount(), body.promoCode());
        return Map.of("id", order.getId(), "version", order.getVersion());
    }

    @GetMapping("/{id}")
    public Map<String, Object> get(@PathVariable Long id) {
        ShopOrder order = orders.find(id);
        return Map.of("id", order.getId(), "status", order.getStatus(), "version", order.getVersion());
    }

    @PostMapping("/{id}/confirm")
    public Map<String, Object> confirm(@PathVariable Long id) {
        ShopOrder order = orders.confirm(id);
        return Map.of("id", order.getId(), "status", order.getStatus());
    }

    @PostMapping("/{id}/cancel")
    public Map<String, Object> cancel(@PathVariable Long id, @RequestParam long version) {
        ShopOrder order = orders.cancel(id, version);
        return Map.of("id", order.getId(), "status", order.getStatus());
    }

    /** mode : normal, slow (timeout), unavailable (503), backup (connexion refusée). */
    @PostMapping("/{id}/pay")
    public String pay(@PathVariable Long id, @RequestParam(defaultValue = "normal") String mode) {
        return payments.pay(id, mode);
    }

    @GetMapping("/{id}/shipping-quote")
    public BigDecimal shippingQuote(@PathVariable Long id) {
        return shipping.quote(orders.find(id).getId());
    }

    @PostMapping("/{id}/fraud-check")
    public boolean fraudCheck(@PathVariable Long id, @RequestParam(defaultValue = "false") boolean certExpired) {
        try {
            return fraud.isSuspicious(id, certExpired);
        } catch (RestClientException e) {
            log.error("Fraud check unavailable for order {}, order kept on hold", id, e);
            throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE, "fraud check unavailable");
        }
    }

    @PostMapping("/{id}/notify")
    public void notifyCustomer(@PathVariable Long id, @RequestParam(defaultValue = "1") int messages) {
        notifications.notifyCustomer(orders.find(id).getId(), messages);
    }
}
