from django.dispatch import receiver

def apply_signals(model, *signals):
    def decorator(func):
        for signal in signals:
            receiver(signal, sender=model)(func)
        return func
    return decorator
