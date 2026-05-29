---- MODULE BoundedQueue_Abs ----
EXTENDS Naturals, Sequences

CONSTANTS Capacity, MaxLen

VARIABLE queue

vars == << queue >>

BSeq(S) == UNION { [1..n -> S] : n \in 0..MaxLen }

Init == queue = << >>

Enqueue(v) ==
  /\ v \in 1..10
  /\ Len(queue) < Capacity
  /\ queue' = Append(queue, v)

Dequeue ==
  /\ Len(queue) > 0
  /\ queue' = Tail(queue)

Next == (\E v \in 1..10 : Enqueue(v)) \/ Dequeue

Spec == Init /\ [][Next]_vars

Inv ==
  /\ queue \in BSeq(1..10)
  /\ Len(queue) \in 0..Capacity

====
