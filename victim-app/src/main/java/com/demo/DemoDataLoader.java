package com.demo;

import com.demo.customer.Customer;
import com.demo.customer.CustomerRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

/** Quelques clients fictifs au démarrage (ids 1 à 3). */
@Component
public class DemoDataLoader implements CommandLineRunner {

    private static final Logger log = LoggerFactory.getLogger(DemoDataLoader.class);

    private final CustomerRepository customers;

    public DemoDataLoader(CustomerRepository customers) {
        this.customers = customers;
    }

    @Override
    public void run(String... args) {
        customers.save(new Customer("alice@example.com", "Alice Martin", "12 rue des Lilas, Lyon"));
        customers.save(new Customer("bob@example.com", "Bob Durand", "4 avenue Foch, Paris"));
        customers.save(new Customer("chloe@example.com", "Chloé Petit", "8 quai Lunel, Bordeaux"));
        log.info("Demo data loaded: {} customers", customers.count());
    }
}
