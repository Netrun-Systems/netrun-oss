# API Reference

## Core Functions

| Function | Description |
|----------|-------------|
| [`configure_logging()`](configure_logging.md) | Configure logging for application |
| [`get_logger()`](get_logger.md) | Get a configured logger instance |

## Correlation ID

| Function | Description |
|----------|-------------|
| [`generate_correlation_id()`](correlation.md#generate_correlation_id) | Generate new UUID correlation ID |
| [`get_correlation_id()`](correlation.md#get_correlation_id) | Get current correlation ID |
| [`set_correlation_id()`](correlation.md#set_correlation_id) | Set correlation ID in context |
| [`correlation_id_context()`](correlation.md#correlation_id_context) | Context manager for scoped IDs |

## Log Context

| Function | Description |
|----------|-------------|
| [`get_context()`](context.md#get_context) | Get current log context |
| [`set_context()`](context.md#set_context) | Set log context values |
| [`clear_context()`](context.md#clear_context) | Clear all context values |

## Formatters

| Class | Description |
|-------|-------------|
| [`JsonFormatter`](json_formatter.md) | JSON log formatter |

## Middleware

| Class | Description |
|-------|-------------|
| [`CorrelationIdMiddleware`](middleware.md#correlationidmiddleware) | FastAPI correlation ID injection |
| [`LoggingMiddleware`](middleware.md#loggingmiddleware) | FastAPI request/response logging |
| [`add_logging_middleware()`](middleware.md#add_logging_middleware) | Helper to add both middlewares |
