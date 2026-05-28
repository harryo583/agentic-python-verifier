---- MODULE Refinement_ProducerConsumerSystem ----
EXTENDS ProducerConsumerSystem

Abs_BoundedQueue == INSTANCE BoundedQueue_Abs WITH
    Capacity <- Capacity,
    MaxLen <- MaxLen,
    queue <- buffer

Abs_Producer == INSTANCE Producer_Abs WITH
    MaxItem <- MaxItem,
    MaxLen <- MaxLen,
    generated <- generated,
    next_item <- next_item

Abs_Consumer == INSTANCE Consumer_Abs WITH
    MaxLen <- MaxLen,
    received <- received,
    sum <- sum

RefinementSpec == /\ Abs_BoundedQueue!Spec
                  /\ Abs_Producer!Spec
                  /\ Abs_Consumer!Spec

====
