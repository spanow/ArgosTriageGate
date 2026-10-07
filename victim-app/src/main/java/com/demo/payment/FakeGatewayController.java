package com.demo.payment;

import java.util.concurrent.ThreadLocalRandom;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/** Faux prestataire de paiement, servi par l'appli elle-même pour rester hors ligne. */
@RestController
@RequestMapping("/fake-gateway")
public class FakeGatewayController {

    @PostMapping("/charge")
    public ResponseEntity<String> charge(@RequestParam Long orderId, @RequestParam String simulate)
            throws InterruptedException {
        switch (simulate) {
            case "slow" -> Thread.sleep(2_000);
            case "unavailable" -> {
                return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE).body("{\"error\":\"maintenance\"}");
            }
            default -> Thread.sleep(ThreadLocalRandom.current().nextInt(50, 700));
        }
        return ResponseEntity.ok("{\"transactionId\":\"tx-" + orderId + "\",\"status\":\"ACCEPTED\"}");
    }
}
