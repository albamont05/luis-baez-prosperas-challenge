import functools
import time
import logging
import asyncio

logger = logging.getLogger(__name__)

class CircuitBreakerOpenException(Exception):
    """Exception raised when attempting to execute a function while the circuit is OPEN."""
    pass

class CircuitBreaker:
    """
    Un Circuit Breaker genérico capaz de envolver funciones síncronas y asíncronas
    como un decorador.
    """
    def __init__(self, failure_threshold: int = 3, recovery_timeout: int = 15):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def __call__(self, func):
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                self._check_state()
                if self.state == "OPEN":
                    raise CircuitBreakerOpenException(f"Circuit breaker for {func.__name__} is OPEN")
                try:
                    result = await func(*args, **kwargs)
                    self._on_success(func.__name__)
                    return result
                except Exception as e:
                    self._on_failure(func.__name__, e)
                    raise e
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                self._check_state()
                if self.state == "OPEN":
                    raise CircuitBreakerOpenException(f"Circuit breaker for {func.__name__} is OPEN")
                try:
                    result = func(*args, **kwargs)
                    self._on_success(func.__name__)
                    return result
                except Exception as e:
                    self._on_failure(func.__name__, e)
                    raise e
            return sync_wrapper

    def _check_state(self):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                logger.info("Circuit breaker state changed to HALF_OPEN (Testing recovery)")

    def _on_success(self, func_name):
        if self.state != "CLOSED":
            logger.info(f"Circuit breaker for {func_name} state changed to CLOSED. Recovered successfully.")
        self.failure_count = 0
        self.state = "CLOSED"

    def _on_failure(self, func_name, exception):
        if self.state == "HALF_OPEN":
            self.state = "OPEN"
            self.last_failure_time = time.time()
            logger.error(f"Circuit breaker for {func_name} failed during HALF_OPEN. Re-opening circuit. Error: {exception}")
            return

        self.failure_count += 1
        self.last_failure_time = time.time()
        logger.warning(f"Circuit breaker for {func_name} recorded a failure: {self.failure_count}/{self.failure_threshold}. Error: {exception}")
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.error(f"Circuit breaker for {func_name} state changed to OPEN. System protected from cascading failures.")

# Instancias predefinidas para BD y AWS
db_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=15)
aws_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=15)
