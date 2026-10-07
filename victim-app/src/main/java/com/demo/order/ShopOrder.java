package com.demo.order;

import com.demo.customer.Customer;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.Id;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import java.math.BigDecimal;

@Entity
@Table(name = "orders")
public class ShopOrder {

    public enum Status { CREATED, CONFIRMED, PAID, CANCELLED }

    @Id
    @GeneratedValue
    private Long id;

    @ManyToOne
    private Customer customer;

    private BigDecimal amount;

    private Status status = Status.CREATED;

    @Version
    private long version;

    protected ShopOrder() {
    }

    public ShopOrder(Customer customer, BigDecimal amount) {
        this.customer = customer;
        this.amount = amount;
    }

    public Long getId() {
        return id;
    }

    public Customer getCustomer() {
        return customer;
    }

    public BigDecimal getAmount() {
        return amount;
    }

    public Status getStatus() {
        return status;
    }

    public void setStatus(Status status) {
        this.status = status;
    }

    public long getVersion() {
        return version;
    }

    public void setVersion(long version) {
        this.version = version;
    }
}
