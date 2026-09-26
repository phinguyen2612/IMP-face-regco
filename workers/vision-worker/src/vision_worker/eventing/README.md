# Recognition eventing

Recognition policy output will enter cooldown/deduplication here before publication to
the control API. Inference adapters must never send frontend notifications directly.
