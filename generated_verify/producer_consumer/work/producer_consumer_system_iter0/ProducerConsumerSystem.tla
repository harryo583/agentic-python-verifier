---- MODULE ProducerConsumerSystem ----
EXTENDS Naturals, Sequences

CONSTANTS Capacity, MaxItem

VARIABLES buffer, generated, next_item, received, sum, pcQ, pcP, pcC

Q == INSTANCE BoundedQueue_Impl WITH buffer <- buffer, Capacity <- Capacity, pc <- pcQ
P == INSTANCE Producer_Impl WITH generated <- generated, next_item <- next_item, MaxItem <- MaxItem, pc <- pcP
C == INSTANCE Consumer_Impl WITH received <- received, sum <- sum, pc <- pcC

Spec == Q!Spec /\ P!Spec /\ C!Spec

SumSeq[s \in Seq(1..10)] ==
  IF s = << >> THEN 0 ELSE Head(s) + SumSeq[Tail(s)]

IsPrefix(a, b) ==
  /\ Len(a) <= Len(b)
  /\ \A i \in 1..Len(a) : a[i] = b[i]

Inv ==
  /\ Q!Inv
  /\ P!Inv
  /\ C!Inv
  /\ Len(buffer) \in 0..Capacity
  /\ IsPrefix(received, generated)
  /\ next_item \in 1..(MaxItem+1)
  /\ generated \in Seq(1..MaxItem)
  /\ received \in Seq(1..MaxItem)

Property ==
  /\ Len(buffer) \in 0..Capacity
  /\ IsPrefix(received, generated)
  /\ next_item <= MaxItem + 1

====
