---- MODULE RWLock_Impl ----
EXTENDS Naturals

CONSTANTS MaxReaders

(* --algorithm RWLock
variables state = "free"; reader_count = 0;
begin
  Loop:
    while TRUE do
      either
        await state \in {"free", "read"};
        await reader_count < MaxReaders;
        state := "read";
        reader_count := reader_count + 1;
      or
        await state = "read";
        await reader_count > 0;
        if reader_count - 1 = 0 then
          state := "free";
        end if;
        reader_count := reader_count - 1;
      or
        await state = "free";
        await reader_count = 0;
        state := "write";
      or
        await state = "write";
        state := "free";
      end either;
    end while;
  Finish:
    skip;
end algorithm; *)
\* BEGIN TRANSLATION (chksum(pcal) = "5faf996d" /\ chksum(tla) = "8dc84c2b")
VARIABLES state, reader_count, pc

vars == << state, reader_count, pc >>

Init == (* Global variables *)
        /\ state = "free"
        /\ reader_count = 0
        /\ pc = "Loop"

Loop == /\ pc = "Loop"
        /\ \/ /\ state \in {"free", "read"}
              /\ reader_count < MaxReaders
              /\ state' = "read"
              /\ reader_count' = reader_count + 1
           \/ /\ state = "read"
              /\ reader_count > 0
              /\ IF reader_count - 1 = 0
                    THEN /\ state' = "free"
                    ELSE /\ TRUE
                         /\ state' = state
              /\ reader_count' = reader_count - 1
           \/ /\ state = "free"
              /\ reader_count = 0
              /\ state' = "write"
              /\ UNCHANGED reader_count
           \/ /\ state = "write"
              /\ state' = "free"
              /\ UNCHANGED reader_count
        /\ pc' = "Loop"

Finish == /\ pc = "Finish"
          /\ TRUE
          /\ pc' = "Done"
          /\ UNCHANGED << state, reader_count >>

(* Allow infinite stuttering to prevent deadlock on termination. *)
Terminating == pc = "Done" /\ UNCHANGED vars

Next == Loop \/ Finish
           \/ Terminating

Spec == Init /\ [][Next]_vars

Termination == <>(pc = "Done")

\* END TRANSLATION 

Inv ==
  /\ state \in {"free", "read", "write"}
  /\ reader_count \in 0..MaxReaders
  /\ (state = "write") => (reader_count = 0)
  /\ (state = "free") => (reader_count = 0)
  /\ (state = "read") => (reader_count >= 1)
  /\ pc \in {"Loop", "Finish", "Done"}

Property == Inv
====
