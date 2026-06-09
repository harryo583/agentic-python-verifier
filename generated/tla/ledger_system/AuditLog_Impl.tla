---- MODULE AuditLog_Impl ----
EXTENDS Naturals, Sequences, TLC

CONSTANTS Accts, Amounts, MaxLogLen

(* --algorithm AuditLog
variables log = << >>;
begin
  Loop:
    while TRUE do
      with from \in Accts, to \in Accts, amt \in Amounts do
        await from # to;
        await Len(log) < MaxLogLen;
        log := Append(log, [from |-> from, to |-> to, amount |-> amt]);
      end with;
    end while;
  Finish:
    skip;
end algorithm; *)
\* BEGIN TRANSLATION (chksum(pcal) = "e92fca7" /\ chksum(tla) = "6be80ada")
VARIABLES log, pc

vars == << log, pc >>

Init == (* Global variables *)
        /\ log = << >>
        /\ pc = "Loop"

Loop == /\ pc = "Loop"
        /\ \E from \in Accts:
             \E to \in Accts:
               \E amt \in Amounts:
                 /\ from # to
                 /\ Len(log) < MaxLogLen
                 /\ log' = Append(log, [from |-> from, to |-> to, amount |-> amt])
        /\ pc' = "Loop"

Finish == /\ pc = "Finish"
          /\ TRUE
          /\ pc' = "Done"
          /\ log' = log

(* Allow infinite stuttering to prevent deadlock on termination. *)
Terminating == pc = "Done" /\ UNCHANGED vars

Next == Loop \/ Finish
           \/ Terminating

Spec == Init /\ [][Next]_vars

Termination == <>(pc = "Done")

\* END TRANSLATION 

EntryT == [from: Accts, to: Accts, amount: Amounts]

BoundedSeq == UNION { [1..n -> EntryT] : n \in 0..MaxLogLen }

TypeOK == log \in BoundedSeq

WellFormed ==
  \A i \in 1..Len(log):
    /\ log[i].amount \in Amounts
    /\ log[i].from # log[i].to

Inv ==
  /\ TypeOK
  /\ WellFormed
  /\ pc \in {"Loop", "Finish", "Done"}

Property == WellFormed
====
