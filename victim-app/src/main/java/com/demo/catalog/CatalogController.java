package com.demo.catalog;

import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;
import tools.jackson.core.JacksonException;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

@RestController
public class CatalogController {

    private static final Logger log = LoggerFactory.getLogger(CatalogController.class);

    /** Flux catalogue reçus des fournisseurs ; celui de « acme » est tronqué (JSON invalide). */
    private static final Map<String, String> SUPPLIER_FEEDS = Map.of(
            "globex", "[{\"sku\":\"GX-100\",\"price\":19.9},{\"sku\":\"GX-200\",\"price\":4.5}]",
            "acme", "[{\"sku\":\"AC-1\",\"price\":12.0},{\"sku\":\"AC-2\",\"price\":");

    private final ObjectMapper objectMapper;

    public CatalogController(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    /** Bruit : consultations normales, WARN de stock bas et d'API dépréciée. */
    @GetMapping("/products/{id}")
    public Map<String, Object> product(@PathVariable int id,
                                       @RequestHeader(value = "X-Api-Version", defaultValue = "2") int apiVersion) {
        if (apiVersion < 2) {
            log.warn("Deprecated API version {} used on /products", apiVersion);
        }
        int stock = (id * 7) % 23;
        if (stock < 4) {
            log.warn("Low stock for product {}: {} left", id, stock);
        }
        log.info("Product {} viewed", id);
        return Map.of("id", id, "stock", stock);
    }

    /** Scénario « JSON invalide » : vrai échec de parsing Jackson sur un flux fournisseur. */
    @PostMapping("/catalog/import")
    public int importFeed(@RequestParam String supplier) {
        String feed = SUPPLIER_FEEDS.getOrDefault(supplier, "[]");
        try {
            JsonNode items = objectMapper.readTree(feed);
            log.info("Catalog import from {}: {} items", supplier, items.size());
            return items.size();
        } catch (JacksonException e) {
            log.error("Catalog import failed for supplier {}", supplier, e);
            throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY, "invalid feed");
        }
    }
}
