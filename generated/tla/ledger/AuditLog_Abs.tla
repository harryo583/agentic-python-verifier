---- MODULE AuditLog_Abs ----
EXTENDS Naturals, Sequences

CONSTANTS Accts, Amounts, MaxLen

VARIABLES log

vars == << log >>

Entry == Accts \X Accts \X Amounts

BoundedSeqs == UNION { [1..k -> Entry] : k \in 0..MaxLen }

Init == log = << >>

Append1(f, t, n) ==
  /\ f \in Accts
  /\ t \in Accts
  /\ n \in Amounts
  /\ Len(log) < MaxLen
  /\ log' = Append(log, << f, t, n >>)

Next ==
  \/ \E f \in Accts, t \in Accts, n \in Amounts : Append1(f, t, n)
  \/ UNCHANGED log

Spec == Init /\ [][Next]_vars

Inv ==
  /\ log \in BoundedSeqs

Property == Inv
====
