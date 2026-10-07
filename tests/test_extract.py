"""Tests de l'extraction d'incident. Extraits raccourcis de logs de victim-app."""

from triage.preprocessing.extract import extract, normalize

NPE_TOMCAT = """\
2026-10-05T13:44:17.001+02:00 ERROR [req=e4855aa1016b] 92196 --- [victim-app] [http-nio-8080-exec-2] o.a.c.c.C.[.[.[/].[dispatcherServlet]    : Servlet.service() for servlet [dispatcherServlet] in context with path [] threw exception [Request processing failed: java.lang.NullPointerException: Cannot invoke "com.demo.customer.Customer.getAddress()" because "customer" is null] with root cause

java.lang.NullPointerException: Cannot invoke "com.demo.customer.Customer.getAddress()" because "customer" is null
\tat com.demo.order.OrderService.validate(OrderService.java:45) ~[classes/:na]
\tat com.demo.order.OrderService.create(OrderService.java:36) ~[classes/:na]
\tat java.base/jdk.internal.reflect.DirectMethodHandleAccessor.invoke(DirectMethodHandleAccessor.java:103) ~[na:na]
\tat org.springframework.aop.support.AopUtils.invokeJoinpointUsingReflection(AopUtils.java:359) ~[spring-aop-7.0.9.jar:7.0.9]
\tat com.demo.order.OrderService$$SpringCGLIB$$0.create(<generated>) ~[classes/:na]
\tat com.demo.order.OrderController.create(OrderController.java:48) ~[classes/:na]
\tat org.apache.catalina.core.ApplicationFilterChain.doFilter(ApplicationFilterChain.java:130) ~[tomcat-embed-core-11.0.24.jar:11.0.24]
"""

PAYMENT_TIMEOUT = """\
2026-10-05T13:44:24.891+02:00 ERROR [req=e4855aa1016b] 92196 --- [victim-app] [http-nio-8080-exec-6] com.demo.payment.PaymentService          : Payment failed for order 19

org.springframework.web.client.RestClientException: Error while extracting response for type [java.lang.String] and content type [application/octet-stream]
\tat org.springframework.web.client.DefaultRestClient.readWithMessageConverters(DefaultRestClient.java:274) ~[spring-web-7.0.9.jar:7.0.9]
\tat com.demo.payment.PaymentGatewayClient.charge(PaymentGatewayClient.java:33) ~[classes/:na]
\tat com.demo.payment.PaymentService.pay(PaymentService.java:31) ~[classes/:na]
Caused by: java.net.SocketTimeoutException: Read timed out
\tat java.base/sun.nio.ch.NioSocketImpl.timedRead(NioSocketImpl.java:278) ~[na:na]
\t... 45 common frames omitted
"""

DUPLICATE_MULTI_EVENT = """\
2026-10-05T13:44:17.815+02:00  WARN [req=a53f8a28abf3] 92196 --- [victim-app] [http-nio-8080-exec-8] org.hibernate.orm.jdbc.error             : HHH000247: ErrorCode: 23505, SQLState: 23505
2026-10-05T13:44:17.819+02:00 ERROR [req=a53f8a28abf3] 92196 --- [victim-app] [http-nio-8080-exec-8] o.a.c.c.C.[.[.[/].[dispatcherServlet]    : Servlet.service() threw exception with root cause

org.h2.jdbc.JdbcSQLIntegrityConstraintViolationException: Unique index or primary key violation: "PUBLIC.CUSTOMER(EMAIL) VALUES ( /* 1 */ 'alice@example.com' )"; SQL statement:
insert into customer (address,email,name,id) values (?,?,?,?) [23505-240]
\tat org.h2.message.DbException.getJdbcSQLException(DbException.java:520) ~[h2-2.4.240.jar:2.4.240]
\tat com.demo.customer.CustomerController.register(CustomerController.java:28) ~[classes/:na]
"""

SAX_WITH_SEMICOLON = """\
2026-09-28T12:31:07.502+02:00 ERROR 2211 --- [billing-service] [sftp-poller-1] c.a.billing.SupplierInvoiceReader : Invoice INV-77120 from supplier 4021 rejected
org.xml.sax.SAXParseException; lineNumber: 57; columnNumber: 14; The element type "Amount" must be terminated by the matching end-tag "</Amount>".
\tat java.xml/com.sun.org.apache.xerces.internal.parsers.DOMParser.parse(DOMParser.java:262)
\tat com.acme.billing.SupplierInvoiceReader.read(SupplierInvoiceReader.java:33)
"""

NOT_A_LOG = "Bonjour, depuis hier je n'arrive plus à valider mon panier.\nMerci, Sophie"


def test_header_is_parsed_and_request_id_dropped():
    event = extract(PAYMENT_TIMEOUT).events[0]
    assert event.level == "ERROR"
    assert event.logger == "com.demo.payment.PaymentService"
    assert event.message == "Payment failed for order 19"
    assert "e4855aa1016b" not in extract(PAYMENT_TIMEOUT).to_text()


def test_root_cause_is_the_last_caused_by():
    incident = extract(PAYMENT_TIMEOUT)
    assert [e.type for e in incident.events[0].chain] == [
        "org.springframework.web.client.RestClientException", "java.net.SocketTimeoutException"]
    assert incident.root_cause.type == "java.net.SocketTimeoutException"
    assert incident.root_cause.message == "Read timed out"


def test_only_application_frames_are_kept_without_generated_proxies():
    frames = extract(NPE_TOMCAT).events[0].frames
    assert frames == ["com.demo.order.OrderService.validate", "com.demo.order.OrderService.create",
                      "com.demo.order.OrderController.create"]


def test_one_incident_can_hold_several_events():
    incident = extract(DUPLICATE_MULTI_EVENT)
    assert [e.level for e in incident.events] == ["WARN", "ERROR"]
    assert incident.root_cause.type == "org.h2.jdbc.JdbcSQLIntegrityConstraintViolationException"


def test_exception_message_continuation_lines_are_kept_as_details():
    event = extract(DUPLICATE_MULTI_EVENT).events[1]
    assert any(line.startswith("insert into customer") for line in event.details)


def test_exception_with_semicolon_separator_and_module_prefixed_frames():
    event = extract(SAX_WITH_SEMICOLON).events[0]
    assert event.chain[0].type == "org.xml.sax.SAXParseException"
    assert "Amount" in event.chain[0].message
    assert event.frames == ["com.acme.billing.SupplierInvoiceReader.read"]


def test_text_that_is_not_a_log_becomes_a_single_raw_event():
    incident = extract(NOT_A_LOG)
    assert len(incident.events) == 1
    assert incident.events[0].level is None
    assert incident.root_cause is None
    assert "panier" in incident.to_text()


def test_compact_text_is_much_shorter_and_keeps_the_root_cause():
    text = extract(PAYMENT_TIMEOUT).to_text()
    assert "Caused by: java.net.SocketTimeoutException: Read timed out" in text
    assert "DefaultRestClient" not in text
    assert len(text.splitlines()) < len(PAYMENT_TIMEOUT.splitlines())


def test_normalize_masks_ids_ips_dates_and_emails_but_keeps_http_codes():
    text = normalize("user alice@example.com from 10.4.2.17:6379 id 8585fd4f-a78b-4ebc-97e0-7eb6189a82b1 "
                     "order 1234567 on 2026-10-08 got 403 after 588 ms, SQLState 23505")
    assert text == "user <EMAIL> from <IP> id <UUID> order <NUM> on <DATE> got 403 after 588 ms, SQLState 23505"


FAILURE_ANALYSIS = """2026-09-25T07:30:01.004+02:00 ERROR 92 --- [notifier] [main] o.s.b.d.LoggingFailureAnalysisReporter :

***************************
APPLICATION FAILED TO START
***************************

Description:

Failed to bind properties under 'notifier.smtp.port' to java.lang.Integer:

    Property: notifier.smtp.port
    Value: "${SMTP_PORT}"
    Origin: class path resource [application.yml] - 14:13
    Reason: failed to convert java.lang.String to java.lang.Integer

Action:

Update your application's configuration
"""


def test_decorative_lines_are_dropped_so_that_the_reason_is_kept():
    details = extract(FAILURE_ANALYSIS).events[0].details
    assert not any(line.startswith("***") for line in details)
    assert "Reason: failed to convert java.lang.String to java.lang.Integer" in details


def test_repeated_causes_and_details_appear_once():
    nested = PAYMENT_TIMEOUT.replace("	... 45 common frames omitted",
                                     "Caused by: java.net.SocketTimeoutException: Read timed out")
    text = extract(nested).to_text()
    assert text.count("SocketTimeoutException") == 1
