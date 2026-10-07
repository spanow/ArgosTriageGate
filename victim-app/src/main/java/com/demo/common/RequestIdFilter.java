package com.demo.common;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.UUID;
import org.slf4j.MDC;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

/** Place l'identifiant de requête (en-tête X-Request-Id, sinon un UUID) dans le MDC : il apparaît dans chaque log. */
@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
public class RequestIdFilter extends OncePerRequestFilter {

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        String requestId = request.getHeader("X-Request-Id");
        // Pas de MDC.remove() en sortie : Tomcat journalise les exceptions non rattrapées APRÈS ce filtre, et on veut
        // l'identifiant sur ces lignes aussi. La requête suivante sur ce thread écrase la valeur.
        MDC.put("requestId", requestId != null ? requestId : UUID.randomUUID().toString());
        chain.doFilter(request, response);
    }
}
