---- MODULE AuditLog_Abs ----
EXTENDS Naturals, Sequences

CONSTANTS Accts, Amounts, MaxLogLen

VARIABLES log

vars == << log >>

Entry == [from: Accts, to: Accts, amount: Amounts]

BoundedLog == UNION { [1..n -> Entry] : n \in 0..MaxLogLen }

TypeOK == log \in BoundedLog

Init == log = << >>

DoAppend(f, t, amt) ==
  /\ f \in Accts /\ t \in Accts /\ f # t
  /\ amt \in Amounts
  /\ Len(log) < MaxLogLen
  /\ log' = Append(log, [from |-> f, to |-> t, amount |-> amt])

Next ==
  \/ \E f, t \in Accts, amt \in Amounts : DoAppend(f, t, amt)
  \/ UNCHANGED vars

Spec == Init /\ [][Next]_vars

WellFormed ==
  \A i \in 1..Len(log) :
    /\ log[i].from # log[i].to
    /\ log[i].amount > 0

Inv == TypeOK /\ WellFormed

Property == WellFormed

====
