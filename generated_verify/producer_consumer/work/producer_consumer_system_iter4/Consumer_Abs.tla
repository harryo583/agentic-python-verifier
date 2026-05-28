---- MODULE Consumer_Abs ----
EXTENDS Naturals, Sequences

CONSTANTS MaxVal, MaxLen

VARIABLES received, sum

vars == <<received, sum>>

SumOf(s) == LET F[i \in 0..Len(s)] == IF i = 0 THEN 0 ELSE F[i-1] + s[i] IN F[Len(s)]
BSeq(S, n) == UNION { [(1..k) -> S] : k \in 0..n }

Init == /\ received = <<>>
        /\ sum = 0

Consume(v) == /\ Len(received) < MaxLen
              /\ received' = Append(received, v)
              /\ sum' = sum + v

Next == (\E v \in 1..MaxVal: Consume(v)) \/ (received' = received /\ sum' = sum)

Spec == Init /\ [][Next]_vars

Inv == /\ received \in BSeq(1..MaxVal, MaxLen)
       /\ sum \in 0..(MaxLen * MaxVal)
       /\ sum = SumOf(received)

Property == sum >= 0
====
