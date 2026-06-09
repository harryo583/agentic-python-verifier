---- MODULE Coordinator_Impl ----
EXTENDS Naturals, FiniteSets, TLC

CONSTANTS RMIDs, Decisions

(* --algorithm Coordinator
variables votes = {}, decision = "none";
begin
  CoLoop:
    while TRUE do
      either
        await decision = "none";
        with r \in RMIDs do
          votes := votes \cup {r};
        end with;
      or
        await decision = "none" /\ votes = RMIDs;
        decision := "commit";
      or
        await decision = "none";
        decision := "abort";
      end either;
    end while;
  Finish:
    skip;
end algorithm; *)
\* BEGIN TRANSLATION (chksum(pcal) = "ec385770" /\ chksum(tla) = "b7bcbfa8")
VARIABLES votes, decision, pc

vars == << votes, decision, pc >>

Init == (* Global variables *)
        /\ votes = {}
        /\ decision = "none"
        /\ pc = "CoLoop"

CoLoop == /\ pc = "CoLoop"
          /\ \/ /\ decision = "none"
                /\ \E r \in RMIDs:
                     votes' = (votes \cup {r})
                /\ UNCHANGED decision
             \/ /\ decision = "none" /\ votes = RMIDs
                /\ decision' = "commit"
                /\ votes' = votes
             \/ /\ decision = "none"
                /\ decision' = "abort"
                /\ votes' = votes
          /\ pc' = "CoLoop"

Finish == /\ pc = "Finish"
          /\ TRUE
          /\ pc' = "Done"
          /\ UNCHANGED << votes, decision >>

(* Allow infinite stuttering to prevent deadlock on termination. *)
Terminating == pc = "Done" /\ UNCHANGED vars

Next == CoLoop \/ Finish
           \/ Terminating

Spec == Init /\ [][Next]_vars

Termination == <>(pc = "Done")

\* END TRANSLATION 

Inv ==
  /\ votes \in SUBSET RMIDs
  /\ decision \in Decisions
  /\ (decision = "commit") => (votes = RMIDs)
  /\ pc \in {"CoLoop", "Finish", "Done"}

Property == (decision = "commit") => (votes = RMIDs)
====
