package com.demo.order;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Service;

@Service
public class DiscountService {

    private static final Map<String, List<BigDecimal>> RATES_BY_CODE = Map.of(
            "WELCOME10", List.of(new BigDecimal("0.10")),
            "SUMMER", List.of(),            // campagne terminée : plus aucun taux
            "VIP", List.of(new BigDecimal("0.20"), new BigDecimal("0.15")));

    /** Scénario « bug de code » : le code SUMMER n'a plus de taux, `get(0)` lève une IndexOutOfBoundsException. */
    public BigDecimal apply(BigDecimal amount, String promoCode) {
        List<BigDecimal> rates = RATES_BY_CODE.getOrDefault(promoCode, List.of(BigDecimal.ZERO));
        BigDecimal bestRate = rates.get(0);
        return amount.subtract(amount.multiply(bestRate));
    }
}
