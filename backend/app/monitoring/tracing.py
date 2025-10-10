"""
Distributed Tracing with OpenTelemetry
"""

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import Resource
import structlog

logger = structlog.get_logger()


def setup_tracing(app, service_name: str = "nrtaxai-backend"):
    """Setup OpenTelemetry tracing for FastAPI app"""
    
    # Create resource
    resource = Resource.create({
        "service.name": service_name,
        "service.version": "1.0.0",
        "deployment.environment": "production"
    })
    
    # Create tracer provider
    tracer_provider = TracerProvider(resource=resource)
    
    # Configure OTLP exporter (sends to CloudWatch or any OTLP collector)
    otlp_exporter = OTLPSpanExporter(
        endpoint="localhost:4317",  # Configure for your OTLP collector
        insecure=True
    )
    
    # Add span processor
    span_processor = BatchSpanProcessor(otlp_exporter)
    tracer_provider.add_span_processor(span_processor)
    
    # Set global tracer provider
    trace.set_tracer_provider(tracer_provider)
    
    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(app)
    
    # Instrument HTTP client
    HTTPXClientInstrumentor().instrument()
    
    logger.info("Tracing initialized", service_name=service_name)


def get_tracer(name: str = "nrtaxai"):
    """Get tracer instance"""
    return trace.get_tracer(name)


# Custom span decorator
def traced_operation(operation_name: str):
    """Decorator to trace custom operations"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            tracer = get_tracer()
            with tracer.start_as_current_span(operation_name) as span:
                span.set_attribute("operation", operation_name)
                try:
                    result = await func(*args, **kwargs)
                    span.set_attribute("status", "success")
                    return result
                except Exception as e:
                    span.set_attribute("status", "error")
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e))
                    raise
        return wrapper
    return decorator
