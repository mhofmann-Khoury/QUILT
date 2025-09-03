import cast_ons;

with Carrier as c:{
	cast_ons.alt_tuck_cast_on(width, tuck_lines=1, knit_lines=0);
	releasehook;
	for _ in range(0, height,2):{
		in reverse direction:{
			knit Loops;
		}
		front_cable = Front_Loops[1::3];
		xfer Front_Loops[2::3] 1 to Left to Back bed;
		xfer front_cable 1 to Right to Back bed;
		xfer Back_Loops across to Front bed;
		in reverse direction:{
			knit Loops;
		}
	}
}
