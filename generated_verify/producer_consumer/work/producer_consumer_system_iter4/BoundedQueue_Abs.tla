---- MODULE BoundedQueue_Abs ----
EXTENDS Naturals, Sequences

CONSTANTS Capacity, MaxVal

VARIABLES queue

vars == <<queue>>

BSeq(S, n) == UNION { [(1..k) -> S] : k \in 0..n }

Init == queue = <<>>

Enqueue(v) == /\ Len(queue) < Capacity
              /\ queue' = Append(queue, v)

Dequeue == /\ Len(queue) > 0
           /\ queue' = Tail(queue)

Next == (\E v \in 1..MaxVal: Enqueue(v)) \/ Dequeue \/ (queue' = queue)

Spec == Init /\ [][Next]_vars

Inv == queue \in BSeq(1..MaxVal, Capacity)

Property == Len(queue) \in 0..Capacity
====
