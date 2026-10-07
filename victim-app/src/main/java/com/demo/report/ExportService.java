package com.demo.report;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

/**
 * Scénario « mémoire épuisée » : l'export prépare un tampon pour tout l'historique d'un coup.
 * Le tableau demandé (8 Go) dépasse le tas : la JVM lève un vrai OutOfMemoryError « Java heap space »
 * sans rien allouer, donc sans mettre l'appli en danger.
 */
@Service
public class ExportService {

    private static final Logger log = LoggerFactory.getLogger(ExportService.class);

    private static final int HISTORY_ROWS = Integer.MAX_VALUE / 2;

    public int exportAllOrders() {
        log.info("Starting full order export ({} rows)", HISTORY_ROWS);
        long[] buffer = new long[HISTORY_ROWS];
        return buffer.length;
    }
}
