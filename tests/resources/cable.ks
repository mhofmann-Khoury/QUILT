import cast_ons;

with Carrier as c:{
	cast_ons.alt_tuck_cast_on(width, tuck_lines=1, knit_lines=0);
	releasehook;
	for _ in range(0, height,2):{
		in reverse direction:{
			knit Loops;
		}
		right_front_loops = Front_Loops[1::6];
		right_back_loops = Front_Loops[4::6];
		left_back_loops = Front_Loops[2::6];
		left_front_loops = Front_Loops[5::6];
		xfer left_back_loops 1 to Left to Back bed;
		xfer right_back_loops 1 to Right to Back bed;
		xfer right_front_loops 1 to Right to Back bed;
		xfer left_front_loops 1 to Left to Back bed;
		xfer Back_Loops across to Front bed;
		in reverse direction:{
			knit Loops;
		}
	}
}
