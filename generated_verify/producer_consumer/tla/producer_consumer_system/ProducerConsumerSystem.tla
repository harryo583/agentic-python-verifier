---- MODULE ProducerConsumerSystem ----
EXTENDS Naturals, Sequences

CONSTANTS Capacity, MaxItem

VARIABLES buffer, generated, nextItem, received, sum, pcQ, pcP, pcC

Q == INSTANCE BoundedQueue_Impl WITH buffer <- buffer, pc <- pcQ, Capacity <- Capacity
P == INSTANCE Producer_Impl WITH generated <- generated, nextItem <- nextItem, pc <- pcP, MaxItem <- MaxItem
C == INSTANCE Consumer_Impl WITH received <- received, sum <- sum, pc <- pcC, MaxLen <- MaxItem, MaxVal <- MaxItem

vars == << buffer, generated, nextItem, received, sum, pcQ, pcP, pcC >>

BSeq(S, n) == UNION { [1..k -> S] : k \in 0..n }

Init ==
  /\ buffer = << >>
  /\ generated = << >>
  /\ nextItem = 1
  /\ received = << >>
  /\ sum = 0
  /\ pcQ = "Loop"
  /\ pcP = "Loop"
  /\ pcC = "Loop"

ProduceStep ==
  /\ nextItem <= MaxItem
  /\ Len(buffer) < Capacity
  /\ buffer' = Append(buffer, nextItem)
  /\ generated' = Append(generated, nextItem)
  /\ nextItem' = nextItem + 1
  /\ UNCHANGED << received, sum, pcQ, pcP, pcC >>

ConsumeStep ==
  /\ Len(buffer) > 0
  /\ received' = Append(received, Head(buffer))
  /\ sum' = sum + Head(buffer)
  /\ buffer' = Tail(buffer)
  /\ UNCHANGED << generated, nextItem, pcQ, pcP, pcC >>

Next == ProduceStep \/ ConsumeStep

Spec == Init /\ [][Next]_vars

IsPrefix(s, t) == Len(s) <= Len(t) /\ \A i \in 1..Len(s) : s[i] = t[i]

RECURSIVE SumOf(_)
SumOf(s) == IF Len(s) = 0 THEN 0 ELSE s[1] + SumOf(Tail(s))

Inv ==
  /\ buffer \in BSeq(1..MaxItem, Capacity)
  /\ generated \in BSeq(1..MaxItem, MaxItem)
  /\ received \in BSeq(1..MaxItem, MaxItem)
  /\ nextItem \in 1..(MaxItem+1)
  /\ sum \in 0..(MaxItem*MaxItem)
  /\ pcQ \in {"Loop", "Finish", "Done"}
  /\ pcP \in {"Loop", "Finish", "Done"}
  /\ pcC \in {"Loop", "Finish", "Done"}
  /\ nextItem = Len(generated) + 1
  /\ sum = SumOf(received)
  /\ IsPrefix(received, generated)
  /\ generated = received \o buffer

Property ==
  /\ Len(buffer) \in 0..Capacity
  /\ IsPrefix(received, generated)
  /\ nextItem <= MaxItem + 1

====
