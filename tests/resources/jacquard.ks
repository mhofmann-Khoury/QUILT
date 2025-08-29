with Carrier as white:{
	in Leftward direction:{
		tuck Front_Needles[0:width:2];
		tuck Back_Needles[1:width:2];
	}
	in Rightward direction:{
		tuck Front_Needles[1:width:2];
		tuck Back_Needles[0:width:2];
	}
}
releasehook;
with Carrier as black:{
	in Leftward direction:{
		knit Front_Needles[0:width:2];
		knit Back_Needles[1:width:2];
	}
	in Rightward direction:{
		knit Front_Needles[1:width:2];
		knit Back_Needles[0:width:2];
	}
}
releasehook;
for _ in range(height-1):{
	with Carrier as white:{
		in reverse direction:{
			knit Front_Loops[0:width/2];
			knit Back_Loops[width/2:];
		}
	}
	with Carrier as black:{
		in current direction:{
			knit Back_Loops[0:width/2];
			knit Front_Loops[width/2:];
		}
	}
}
