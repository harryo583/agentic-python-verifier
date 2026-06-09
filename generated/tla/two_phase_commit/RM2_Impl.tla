---- MODULE RM2_Impl ----
EXTENDS Naturals, TLC

CONSTANTS States

(* --algorithm RM2
variables rm2State = "working";
begin
  RMLoop:
    while TRUE do
      either
        await rm2State = "working";
        rm2State := "prepared";
      or
        await rm2State = "prepared";
        rm2State := "committed";
      or
        await rm2State \in {"working","prepared"};
        rm2State := "aborted";
      end either;
    end while;
  Finish:
    skip;
end algorithm; *)
\* BEGIN TRANSLATION (chksum(pcal) = "c439fea5" /\ chksum(tla) = "661ed623")
VARIABLES rm2State, pc

vars == << rm2State, pc >>

Init == (* Global variables *)
        /\ rm2State = "working"
        /\ pc = "RMLoop"

RMLoop == /\ pc = "RMLoop"
          /\ \/ /\ rm2State = "working"
                /\ rm2State' = "prepared"
             \/ /\ rm2State = "prepared"
                /\ rm2State' = "committed"
             \/ /\ rm2State \in {"working","prepared"}
                /\ rm2State' = "aborted"
          /\ pc' = "RMLoop"

Finish == /\ pc = "Finish"
          /\ TRUE
          /\ pc' = "Done"
          /\ UNCHANGED rm2State

(* Allow infinite stuttering to prevent deadlock on termination. *)
Terminating == pc = "Done" /\ UNCHANGED vars

Next == RMLoop \/ Finish
           \/ Terminating

Spec == Init /\ [][Next]_vars

Termination == <>(pc = "Done")

\* END TRANSLATION 

Inv ==
  /\ rm2State \in States
  /\ pc \in {"RMLoop", "Finish", "Done"}

Property == rm2State \in States
====
