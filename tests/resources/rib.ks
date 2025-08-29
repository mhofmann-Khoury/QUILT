import cast_ons;

with Carrier as c:{
	cast_ons.alt_tuck_cast_on(width, tuck_lines=1, knit_lines=0);
	releasehook;
	xfer Front_Loops[1::2] across to Back bed;
	for _ in range(height):{
		in reverse direction:{
			knit Loops;
		}
	}
}
