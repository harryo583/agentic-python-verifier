---- MODULE AuditLog_Impl ----
EXTENDS Naturals, Sequences, TLC

CONSTANTS Accts, Amounts, MaxLogLen

Entry == [from: Accts, to: Accts, amount: Amounts]

BoundedLog == UNION { [1..n -> Entry] : n \in 0..MaxLogLen }

(* --algorithm AuditLog
variables log = << >>;
begin
  Loop:
    while TRUE do
      with f \in Accts, t \in Accts, amt \in Amounts do
        await f # t;
        await Len(log) < MaxLogLen;
        log := Append(log, [from |-> f, to |-> t, amount |-> amt]);
      end with;
    end while;
  Finish:
    skip;
end algorithm; *)
\* BEGIN TRANSLATION (chksum(pcal) = "a12d1c0a" /\ chksum(tla) = "7b746968")
VARIABLES log, pc

vars == << log, pc >>

Init == (* Global variables *)
        /\ log = << >>
        /\ pc = "Loop"

Loop == /\ pc = "Loop"
        /\ \E f \in Accts:
             \E t \in Accts:
               \E amt \in Amounts:
                 /\ f # t
                 /\ Len(log) < MaxLogLen
                 /\ log' = Append(log, [from |-> f, to |-> t, amount |-> amt])
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

TypeOK == log \in BoundedLog

WellFormed ==
  \A i \in 1..Len(log) :
    /\ log[i].from # log[i].to
    /\ log[i].amount > 0

Inv ==
  /\ TypeOK
  /\ WellFormed
  /\ pc \in {"Loop", "Finish", "Done"}

Property == WellFormed

====
