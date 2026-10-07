package com.demo.customer;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/customers")
public class CustomerController {

    private static final Logger log = LoggerFactory.getLogger(CustomerController.class);

    private final CustomerRepository customers;

    public CustomerController(CustomerRepository customers) {
        this.customers = customers;
    }

    public record NewCustomer(String email, String name, String address) {
    }

    /** Scénario « contrainte d'unicité » : un e-mail déjà pris lève une vraie DataIntegrityViolationException (H2). */
    @PostMapping
    public Long register(@RequestBody NewCustomer body) {
        Customer saved = customers.saveAndFlush(new Customer(body.email(), body.name(), body.address()));
        log.info("Customer registered id={}", saved.getId());
        return saved.getId();
    }
}
