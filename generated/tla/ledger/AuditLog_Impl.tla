---- MODULE AuditLog_Impl ----
EXTENDS Naturals, Sequences, TLC

CONSTANTS Accts, Amounts, MaxLen

Entry == Accts \X Accts \X Amounts

BoundedSeqs == UNION { [1..k -> Entry] : k \in 0..MaxLen }

(* --algorithm AuditLog
variables log = << >>;
begin
  Loop:
    while TRUE do
      with f \in Accts, t \in Accts, n \in Amounts do
        await Len(log) < MaxLen;
        log := Append(log, << f, t, n >>);
      end with;
    end while;
  Finish:
    skip;
end algorithm; *)
\* BEGIN TRANSLATION (chksum(pcal) = "b947f014" /\ chksum(tla) = "551adc4c")
VARIABLES log, pc

vars == << log, pc >>

Init == (* Global variables *)
        /\ log = << >>
        /\ pc = "Loop"

Loop == /\ pc = "Loop"
        /\ \E f \in Accts:
             \E t \in Accts:
               \E n \in Amounts:
                 /\ Len(log) < MaxLen
                 /\ log' = Append(log, << f, t, n >>)
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

Inv ==
  /\ log \in BoundedSeqs
  /\ pc \in {"Loop", "Finish", "Done"}

Property == Inv
====
