---- MODULE ResourceManager_Impl ----
EXTENDS Naturals

(* --algorithm ResourceManager
variables rmState = "working";
begin
  Loop:
    while TRUE do
      either
        await rmState = "working";
        rmState := "prepared";
      or
        await rmState = "prepared";
        rmState := "committed";
      or
        await rmState \in {"working","prepared"};
        rmState := "aborted";
      or
        skip;
      end either;
    end while;
  Finish:
    skip;
end algorithm; *)
\* BEGIN TRANSLATION (chksum(pcal) = "c3d735c5" /\ chksum(tla) = "a423ba55")
VARIABLES rmState, pc

vars == << rmState, pc >>

Init == (* Global variables *)
        /\ rmState = "working"
        /\ pc = "Loop"

Loop == /\ pc = "Loop"
        /\ \/ /\ rmState = "working"
              /\ rmState' = "prepared"
           \/ /\ rmState = "prepared"
              /\ rmState' = "committed"
           \/ /\ rmState \in {"working","prepared"}
              /\ rmState' = "aborted"
           \/ /\ TRUE
              /\ UNCHANGED rmState
        /\ pc' = "Loop"

Finish == /\ pc = "Finish"
          /\ TRUE
          /\ pc' = "Done"
          /\ UNCHANGED rmState

(* Allow infinite stuttering to prevent deadlock on termination. *)
Terminating == pc = "Done" /\ UNCHANGED vars

Next == Loop \/ Finish
           \/ Terminating

Spec == Init /\ [][Next]_vars

Termination == <>(pc = "Done")

\* END TRANSLATION 

States == {"working","prepared","committed","aborted"}

Inv ==
  /\ rmState \in States
  /\ pc \in {"Loop","Finish","Done"}

Property == rmState \in States
====
