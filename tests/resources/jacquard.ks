with Carrier as white:{
	in Leftward direction:{
		tuck Front_Needles[0:width:2];
		tuck Back_Needles[1:width:2];
	}
	releasehook;
}
with Carrier as black:{
	in Leftward direction:{
		tuck Front_Needles[1:width:2];
		tuck Back_Needles[0:width:2];
	}
	releasehook;
}
with Carrier as white:{
	in Rightward direction:{
		tuck Front_Needles[1:width:2];
		tuck Back_Needles[0:width:2];
	}
}
with Carrier as black:{
	in Rightward direction:{
		tuck Front_Needles[0:width:2];
		tuck Back_Needles[1:width:2];
	}
}
for _ in range(0,height,2):{
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
