package com.demo.notification;

import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

/** Scénario « pool de threads saturé » : un seul worker et une file d'une place, la 3ᵉ notification est rejetée. */
@Service
public class NotificationService {

    private static final Logger log = LoggerFactory.getLogger(NotificationService.class);

    private final ThreadPoolExecutor executor =
            new ThreadPoolExecutor(1, 1, 0, TimeUnit.SECONDS, new ArrayBlockingQueue<>(1));

    public void notifyCustomer(Long orderId, int messages) {
        for (int i = 1; i <= messages; i++) {
            int n = i;
            executor.execute(() -> send(orderId, n));
        }
    }

    private void send(Long orderId, int n) {
        try {
            Thread.sleep(1_000);
            log.info("Notification {} sent for order {}", n, orderId);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }
}
