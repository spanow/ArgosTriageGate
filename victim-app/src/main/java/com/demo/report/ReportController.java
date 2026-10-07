package com.demo.report;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/reports")
public class ReportController {

    private final ReportService reports;
    private final ExportService exports;

    public ReportController(ReportService reports, ExportService exports) {
        this.reports = reports;
        this.exports = exports;
    }

    @GetMapping("/sales")
    public long sales() throws InterruptedException {
        return reports.salesReport();
    }

    @GetMapping("/export")
    public int export() {
        return exports.exportAllOrders();
    }
}
