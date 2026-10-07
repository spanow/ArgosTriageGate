package com.demo.order;

import com.demo.customer.Customer;
import com.demo.customer.CustomerRepository;
import jakarta.persistence.EntityManager;
import java.math.BigDecimal;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.http.HttpStatus;

@Service
public class OrderService {

    private static final Logger log = LoggerFactory.getLogger(OrderService.class);

    private final OrderRepository orders;
    private final CustomerRepository customers;
    private final DiscountService discounts;
    private final EntityManager entityManager;

    public OrderService(OrderRepository orders, CustomerRepository customers, DiscountService discounts,
                        EntityManager entityManager) {
        this.orders = orders;
        this.customers = customers;
        this.discounts = discounts;
        this.entityManager = entityManager;
    }

    @Transactional
    public ShopOrder create(Long customerId, BigDecimal amount, String promoCode) {
        // Une commande « invité » arrive sans client : customer reste null.
        Customer customer = customerId == null ? null : customers.findById(customerId).orElse(null);
        validate(customer, amount);
        BigDecimal total = promoCode == null ? amount : discounts.apply(amount, promoCode);
        ShopOrder order = orders.save(new ShopOrder(customer, total));
        log.info("Order created id={} amount={}", order.getId(), total);
        return order;
    }

    /** Scénario « NPE métier » : la validation suppose un client, une commande invité lève une NullPointerException. */
    private void validate(Customer customer, BigDecimal amount) {
        if (customer.getAddress().isBlank()) {
            throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY, "missing address");
        }
        if (amount.signum() <= 0) {
            throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY, "invalid amount");
        }
    }

    @Transactional
    public ShopOrder confirm(Long id) {
        ShopOrder order = find(id);
        order.setStatus(ShopOrder.Status.CONFIRMED);
        log.info("Order confirmed id={}", id);
        return order;
    }

    /**
     * Scénario « modification concurrente » : le client annule avec la version qu'il avait lue.
     * Si la commande a changé entre-temps, Hibernate lève un vrai conflit de verrou optimiste.
     */
    @Transactional
    public ShopOrder cancel(Long id, long expectedVersion) {
        ShopOrder order = find(id);
        entityManager.detach(order);
        order.setVersion(expectedVersion);
        order.setStatus(ShopOrder.Status.CANCELLED);
        ShopOrder merged = orders.saveAndFlush(order);
        log.info("Order cancelled id={}", id);
        return merged;
    }

    @Transactional
    public void markPaid(Long id) {
        find(id).setStatus(ShopOrder.Status.PAID);
    }

    public ShopOrder find(Long id) {
        return orders.findById(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "order " + id));
    }
}
