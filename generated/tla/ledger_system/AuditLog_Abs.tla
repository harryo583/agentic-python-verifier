---- MODULE AuditLog_Abs ----
EXTENDS Naturals, Sequences

CONSTANTS Accts, Amounts, MaxLogLen

VARIABLES log

vars == << log >>

EntryT == [from: Accts, to: Accts, amount: Amounts]

BoundedSeq == UNION { [1..n -> EntryT] : n \in 0..MaxLogLen }

TypeOK == log \in BoundedSeq

Init == log = << >>

Append1(e) ==
  /\ e \in EntryT
  /\ e.from # e.to
  /\ Len(log) < MaxLogLen
  /\ log' = Append(log, e)

Next == \E e \in EntryT: Append1(e)

Spec == Init /\ [][Next]_vars

WellFormed ==
  \A i \in 1..Len(log):
    /\ log[i].amount \in Amounts
    /\ log[i].from # log[i].to

Inv ==
  /\ TypeOK
  /\ WellFormed

Property == WellFormed
====
