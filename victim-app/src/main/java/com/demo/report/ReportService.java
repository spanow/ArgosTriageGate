package com.demo.report;

import com.demo.order.OrderRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Scénario « pool de connexions épuisé » : le rapport garde sa connexion pendant un calcul lent.
 * Avec un pool de 2 et un timeout d'1 s, le 3ᵉ rapport simultané échoue (vraie erreur Hikari).
 */
@Service
public class ReportService {

    private static final Logger log = LoggerFactory.getLogger(ReportService.class);

    private final OrderRepository orders;

    public ReportService(OrderRepository orders) {
        this.orders = orders;
    }

    @Transactional(readOnly = true)
    public long salesReport() throws InterruptedException {
        long count = orders.count();
        Thread.sleep(2_500); // agrégation lente, connexion toujours tenue
        log.info("Sales report computed over {} orders", count);
        return count;
    }
}
