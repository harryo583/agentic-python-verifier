---- MODULE Coordinator_Impl ----
EXTENDS Naturals, Sequences, FiniteSets, TLC
CONSTANTS RMs

CoordStates == {"init", "preparing", "decided"}
VoteVals == {"none", "prepared", "aborted"}
Decisions == {"none", "Commit", "Abort"}
PCs == {"Run", "Finish", "Done"}

(* --algorithm Coordinator
variables
  coordState = "init",
  votes = [r \in RMs |-> "none"],
  decision = "none";
begin
  Run:
    while TRUE do
      either
        await coordState = "init";
        coordState := "preparing";
      or
        with r \in RMs, v \in {"prepared", "aborted"} do
          await coordState = "preparing" /\ votes[r] = "none";
          votes[r] := v;
        end with;
      or
        await coordState = "preparing" /\ decision = "none" /\ (\A r \in RMs : votes[r] = "prepared");
        decision := "Commit";
        coordState := "decided";
      or
        await coordState = "preparing" /\ decision = "none" /\ (\E r \in RMs : votes[r] = "aborted");
        decision := "Abort";
        coordState := "decided";
      end either;
    end while;
  Finish:
    skip;
end algorithm; *)
\* BEGIN TRANSLATION (chksum(pcal) = "e531fde3" /\ chksum(tla) = "6511be32")
VARIABLES coordState, votes, decision, pc

vars == << coordState, votes, decision, pc >>

Init == (* Global variables *)
        /\ coordState = "init"
        /\ votes = [r \in RMs |-> "none"]
        /\ decision = "none"
        /\ pc = "Run"

Run == /\ pc = "Run"
       /\ \/ /\ coordState = "init"
             /\ coordState' = "preparing"
             /\ UNCHANGED <<votes, decision>>
          \/ /\ \E r \in RMs:
                  \E v \in {"prepared", "aborted"}:
                    /\ coordState = "preparing" /\ votes[r] = "none"
                    /\ votes' = [votes EXCEPT ![r] = v]
             /\ UNCHANGED <<coordState, decision>>
          \/ /\ coordState = "preparing" /\ decision = "none" /\ (\A r \in RMs : votes[r] = "prepared")
             /\ decision' = "Commit"
             /\ coordState' = "decided"
             /\ votes' = votes
          \/ /\ coordState = "preparing" /\ decision = "none" /\ (\E r \in RMs : votes[r] = "aborted")
             /\ decision' = "Abort"
             /\ coordState' = "decided"
             /\ votes' = votes
       /\ pc' = "Run"

Finish == /\ pc = "Finish"
          /\ TRUE
          /\ pc' = "Done"
          /\ UNCHANGED << coordState, votes, decision >>

(* Allow infinite stuttering to prevent deadlock on termination. *)
Terminating == pc = "Done" /\ UNCHANGED vars

Next == Run \/ Finish
           \/ Terminating

Spec == Init /\ [][Next]_vars

Termination == <>(pc = "Done")

\* END TRANSLATION 

Inv ==
  /\ pc \in PCs
  /\ coordState \in CoordStates
  /\ decision \in Decisions
  /\ votes \in [RMs -> VoteVals]
  /\ (decision = "Commit") => (\A r \in RMs : votes[r] = "prepared")

Property == Inv
====
