---- MODULE BoundedQueue_Abs ----
EXTENDS Naturals, Sequences
CONSTANTS Capacity
VARIABLES buffer

BSeq(S, n) == UNION { [1..k -> S] : k \in 0..n }

Init == buffer = << >>

Enqueue(v) ==
  /\ Len(buffer) < Capacity
  /\ v \in 1..10
  /\ buffer' = Append(buffer, v)

Dequeue ==
  /\ Len(buffer) > 0
  /\ buffer' = Tail(buffer)

Next == (\E v \in 1..10 : Enqueue(v)) \/ Dequeue

Spec == Init /\ [][Next]_buffer

Inv == buffer \in BSeq(1..10, Capacity)

Property == Len(buffer) \in 0..Capacity
====
