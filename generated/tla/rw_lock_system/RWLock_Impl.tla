---- MODULE RWLock_Impl ----
EXTENDS Naturals

CONSTANTS MaxReaders

(* --algorithm RWLock
variables state = "free", reader_count = 0;
begin
  Loop:
    while TRUE do
      either
        await state \in {"free","read"} /\ reader_count < MaxReaders;
        state := "read";
        reader_count := reader_count + 1;
      or
        await state = "read" /\ reader_count > 0;
        if reader_count - 1 = 0 then
          state := "free";
        end if;
        reader_count := reader_count - 1;
      or
        await state = "free" /\ reader_count = 0;
        state := "write";
      or
        await state = "write";
        state := "free";
      end either;
    end while;
end algorithm; *)
\* BEGIN TRANSLATION (chksum(pcal) = "fabd1687" /\ chksum(tla) = "e0850b4")
VARIABLES state, reader_count

vars == << state, reader_count >>

Init == (* Global variables *)
        /\ state = "free"
        /\ reader_count = 0

Next == \/ /\ state \in {"free","read"} /\ reader_count < MaxReaders
           /\ state' = "read"
           /\ reader_count' = reader_count + 1
        \/ /\ state = "read" /\ reader_count > 0
           /\ IF reader_count - 1 = 0
                 THEN /\ state' = "free"
                 ELSE /\ TRUE
                      /\ state' = state
           /\ reader_count' = reader_count - 1
        \/ /\ state = "free" /\ reader_count = 0
           /\ state' = "write"
           /\ UNCHANGED reader_count
        \/ /\ state = "write"
           /\ state' = "free"
           /\ UNCHANGED reader_count

Spec == Init /\ [][Next]_vars

\* END TRANSLATION 

Inv ==
  /\ state \in {"free","read","write"}
  /\ reader_count \in 0..MaxReaders
  /\ (state = "write") => (reader_count = 0)
  /\ (state = "read")  => (reader_count >= 1)
  /\ (state = "free")  => (reader_count = 0)

Property == Inv
====
