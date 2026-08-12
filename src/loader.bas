10 REM ==== GRAVASSIST loader ====
20 MEMORY &3FFF
30 REM --- splash: MODE 0 me diki tou paleta (assets/revive8b.txt) ---
40 ON ERROR GOTO 200
50 INK 0,0:INK 1,13:INK 2,26:INK 3,15:INK 4,25:INK 5,10:INK 6,3:INK 7,1
60 INK 8,11:INK 9,23:INK 10,6:INK 11,24:INK 12,20:INK 13,16:INK 14,12:INK 15,4
70 BORDER 0:MODE 0
80 LOAD"REVIVE8B.SCR",&C000
90 REM TIME metraei 300 ana defterolepto -> 3000 = 10 defterolepta
100 t=TIME+3000
110 IF INKEY(47)<>-1 THEN 130
120 IF TIME<t THEN 110
130 ON ERROR GOTO 0
140 REM I splash MENEI: to paixnidi allazei se MODE 1 molis einai etoimo
150 REM to menou. I mpara fortosis zografizetai epano tis, se MODE 0.
180 LOAD"MAIN.BIN"
190 CALL &4000
200 REM Xoris to .SCR sto disko, sinexise sto paixnidi anti na skasei
210 RESUME 130
