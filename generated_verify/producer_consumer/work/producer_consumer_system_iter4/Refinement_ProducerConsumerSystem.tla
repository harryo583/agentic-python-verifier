---- MODULE Refinement_ProducerConsumerSystem ----
EXTENDS ProducerConsumerSystem

Abs_BoundedQueue == INSTANCE BoundedQueue_Abs WITH
    Capacity <- Capacity,
    MaxVal <- MaxVal,
    queue <- buffer

Abs_Producer == INSTANCE Producer_Abs WITH
    MaxItem <- MaxItem,
    generated <- generated,
    nextItem <- nextItem

Abs_Consumer == INSTANCE Consumer_Abs WITH
    MaxVal <- MaxVal,
    MaxLen <- MaxLen,
    received <- received,
    sum <- sum

RefinementSpec == /\ Abs_BoundedQueue!Spec
                  /\ Abs_Producer!Spec
                  /\ Abs_Consumer!Spec

====
