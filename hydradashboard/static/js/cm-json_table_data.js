// JavaScript Document

function loadData()
{
		var table;
/* 		"<tr> " +
 			" <th width='13%'>Lustre FS name</th>" +
			"<th width='12%'>MGS Name</th>" +
			"<th width='13%'>MDS Name</th>" +
			"<th width='7%'>No of OSS</th>" +
			"<th width='7%'>No of OST</th>" +
            "<th width='7%'>Used (TB)</th>" +
            "<th width='7%'>Free (TB)</th>" +
            "<th width='15%'>Action</th>" +
		"</tr>" +
	"</thead>";
*/
		//First row
		table = table + "<tr> <td>" + "hulkfs01" + "</td>";
		table = table + "<td>" + "cb-centos-6-s1" + "</td>";
		table = table + "<td>" + "cb-centos-6-s2" + "</td>";
		table = table + "<td>" + "10" + "</td>";
		table = table + "<td>" + "50" + "</td>";
		table = table + "<td>" + "320" + "</td>";
		table = table + "<td>" + "150" + "</td>";
		table = table + "<td>" + "Stop FS | Config param | Remove" + "</td></tr>"; 
		
		//Second row
		table = table + "<tr> <td>" + "neofs01" + "</td>";
		table = table + "<td>" + "cb-centos-6-s1" + "</td>";
		table = table + "<td>" + "cb-centos-6-s2" + "</td>";
		table = table + "<td>" + "10" + "</td>";
		table = table + "<td>" + "50" + "</td>";
		table = table + "<td>" + "320" + "</td>";
		table = table + "<td>" + "150" + "</td>";
		table = table + "<td>" + "Stop FS | Config param | Remove" + "</td></tr>"; 
		
		//third row
		table = table + "<tr> <td>" + "sobofs01" + "</td>";
		table = table + "<td>" + "cb-centos-6-s1" + "</td>";
		table = table + "<td>" + "cb-centos-6-s2" + "</td>";
		table = table + "<td>" + "10" + "</td>";
		table = table + "<td>" + "50" + "</td>";
		table = table + "<td>" + "320" + "</td>";
		table = table + "<td>" + "150" + "</td>";
		table = table + "<td>" + "Stop FS | Config param | Remove" + "</td></tr>"; 
		
		//forth row
		table = table + "<tr> <td>" + "punefs01" + "</td>";
		table = table + "<td>" + "cb-centos-6-s1" + "</td>";
		table = table + "<td>" + "cb-centos-6-s2" + "</td>";
		table = table + "<td>" + "10" + "</td>";
		table = table + "<td>" + "50" + "</td>";
		table = table + "<td>" + "320" + "</td>";
		table = table + "<td>" + "150" + "</td>";
		table = table + "<td>" + "Stop FS | Config param | Remove" + "</td></tr>"; 
		
			
/*	for (var i=0;i<15;i++)
	{
		table = table + "<tr> <td>" + i + "</td>";
		table = table + "<td>" + i + "</td>";
		table = table + "<td>" + i + "</td>";
		table = table + "<td>" + i + "</td>";
		table = table + "<td>" + i + "</td>";
		table = table + "<td>" + i + "</td>";
		table = table + "<td>" + i + "</td>";
		table = table + "<td>" + i + "</td></tr>"; 
	} */

	/* table = table + "</tbody>"; */
	 $('#example_content').html(table); 
}



function loadMgtData()
{
		var table;
	
		//First row
		table = table + "<tr> <td>" + "/dev/disk/by-path/pci-0000:00.1-scsi-0:0:0:0" + "</td>";
		table = table + "<td>" + "flntfs01-MGT0001" + "</td>";
		table = table + "<td>" + "MGT" + "</td>";
		table = table + "<td>" + "<a href='#'>clo-indiana-h1</a>" + "</td>";
		table = table + "<td>" + "<a href='#'>clo-indiana-h2</a>" + "</td>";
		table = table + "<td>" + "OK" + "</td>";
		table = table + "<td>" + "<a href='#'>Format </a> | <a href='#'>Register</a> | <a href='#'>Start</a> | <a href='#'>Remove</a></td></tr>"; 
		
/*		//Second row
		table = table + "<tr> <td>" + "fnifs01" + "</td>";
		table = table + "<td>" + "cb-centos-6-s1" + "</td>";
		table = table + "<td>" + "cb-centos-6-s2" + "</td>";
		table = table + "<td>" + "10" + "</td>";
		table = table + "<td>" + "50" + "</td>";
		table = table + "<td>" + "320" + "</td>";
		table = table + "<td>" + "150" + "</td>";
		table = table + "<td>" + "Stop FS | Config param | Remove" + "</td></tr>"; 
		
		//third row
		table = table + "<tr> <td>" + "fnifs01" + "</td>";
		table = table + "<td>" + "cb-centos-6-s1" + "</td>";
		table = table + "<td>" + "cb-centos-6-s2" + "</td>";
		table = table + "<td>" + "10" + "</td>";
		table = table + "<td>" + "50" + "</td>";
		table = table + "<td>" + "320" + "</td>";
		table = table + "<td>" + "150" + "</td>";
		table = table + "<td>" + "Stop FS | Config param | Remove" + "</td></tr>"; 
		
		//forth row
		table = table + "<tr> <td>" + "fnifs01" + "</td>";
		table = table + "<td>" + "cb-centos-6-s1" + "</td>";
		table = table + "<td>" + "cb-centos-6-s2" + "</td>";
		table = table + "<td>" + "10" + "</td>";
		table = table + "<td>" + "50" + "</td>";
		table = table + "<td>" + "320" + "</td>";
		table = table + "<td>" + "150" + "</td>";
		table = table + "<td>" + "Stop FS | Config param | Remove" + "</td></tr>"; 
		
		//fifth row
		table = table + "<tr> <td>" + "fnifs01" + "</td>";
		table = table + "<td>" + "cb-centos-6-s1" + "</td>";
		table = table + "<td>" + "cb-centos-6-s2" + "</td>";
		table = table + "<td>" + "10" + "</td>";
		table = table + "<td>" + "50" + "</td>";
		table = table + "<td>" + "320" + "</td>";
		table = table + "<td>" + "150" + "</td>";
		table = table + "<td>" + "Stop FS | Config param | Remove" + "</td></tr>"; 
		
		//sixth row
		table = table + "<tr> <td>" + "fnifs01" + "</td>";
		table = table + "<td>" + "cb-centos-6-s1" + "</td>";
		table = table + "<td>" + "cb-centos-6-s2" + "</td>";
		table = table + "<td>" + "10" + "</td>";
		table = table + "<td>" + "50" + "</td>";
		table = table + "<td>" + "320" + "</td>";
		table = table + "<td>" + "150" + "</td>";
		table = table + "<td>" + "Stop FS | Config param | Remove" + "</td></tr>"; */
	
	
/*	for (var i=0;i<2;i++)
	{
		table = table + "<tr> <td>" + i + "</td>";
		table = table + "<td>" + i + "</td>";
		table = table + "<td>" + i + "</td>";
		table = table + "<td>" + i + "</td>";
		table = table + "<td>" + i + "</td>";
		table = table + "<td>" + i + "</td>";
		table = table + "<td>" + i + "</td>";
		table = table + "<td>" + i + "</td></tr>"; 
	}
*/

	 $('#example_content').html(table); 
}

function loadMDTData()
{
		var table;
		
		//First row
		table = table + "<tr><td>" + "/dev/disk/by-path/pci-0000:00.1-scsi-0:0:0:0" + "</td>";
		table = table + "<td>" + "flntfs01-MGT0001" + "</td>";
		table = table + "<td>" + "MDT" + "</td>";
		table = table + "<td>" + "<a href='#'>clo-indiana-h1</a>" + "</td>";
		table = table + "<td>" + "<a href='#'>clo-indiana-h2</a>" + "</td>";
		table = table + "<td>" + "OK" + "</td>";
		table = table + "<td>" + "<a href='#'>Format </a> | <a href='#'>Register</a> | <a href='#'>Start</a> | <a href='#'>Remove</a>" + "</td></tr>"; 
		
/*		//Second row
		table = table + "<tr> <td>" + "fnifs01" + "</td>";
		table = table + "<td>" + "cb-centos-6-s1" + "</td>";
		table = table + "<td>" + "cb-centos-6-s2" + "</td>";
		table = table + "<td>" + "10" + "</td>";
		table = table + "<td>" + "50" + "</td>";
		table = table + "<td>" + "320" + "</td>";
		table = table + "<td>" + "150" + "</td>";
		table = table + "<td>" + "Stop FS | Config param | Remove" + "</td></tr>"; 
		
		//third row
		table = table + "<tr> <td>" + "fnifs01" + "</td>";
		table = table + "<td>" + "cb-centos-6-s1" + "</td>";
		table = table + "<td>" + "cb-centos-6-s2" + "</td>";
		table = table + "<td>" + "10" + "</td>";
		table = table + "<td>" + "50" + "</td>";
		table = table + "<td>" + "320" + "</td>";
		table = table + "<td>" + "150" + "</td>";
		table = table + "<td>" + "Stop FS | Config param | Remove" + "</td></tr>"; 
		
		//forth row
		table = table + "<tr> <td>" + "fnifs01" + "</td>";
		table = table + "<td>" + "cb-centos-6-s1" + "</td>";
		table = table + "<td>" + "cb-centos-6-s2" + "</td>";
		table = table + "<td>" + "10" + "</td>";
		table = table + "<td>" + "50" + "</td>";
		table = table + "<td>" + "320" + "</td>";
		table = table + "<td>" + "150" + "</td>";
		table = table + "<td>" + "Stop FS | Config param | Remove" + "</td></tr>"; 
		
		//fifth row
		table = table + "<tr> <td>" + "fnifs01" + "</td>";
		table = table + "<td>" + "cb-centos-6-s1" + "</td>";
		table = table + "<td>" + "cb-centos-6-s2" + "</td>";
		table = table + "<td>" + "10" + "</td>";
		table = table + "<td>" + "50" + "</td>";
		table = table + "<td>" + "320" + "</td>";
		table = table + "<td>" + "150" + "</td>";
		table = table + "<td>" + "Stop FS | Config param | Remove" + "</td></tr>"; 
		
		//sixth row
		table = table + "<tr> <td>" + "fnifs01" + "</td>";
		table = table + "<td>" + "cb-centos-6-s1" + "</td>";
		table = table + "<td>" + "cb-centos-6-s2" + "</td>";
		table = table + "<td>" + "10" + "</td>";
		table = table + "<td>" + "50" + "</td>";
		table = table + "<td>" + "320" + "</td>";
		table = table + "<td>" + "150" + "</td>";
		table = table + "<td>" + "Stop FS | Config param | Remove" + "</td></tr>"; */
	
	
/*	for (var i=0;i<2;i++)
	{
		table = table + "<tr> <td>" + i + "</td>";
		table = table + "<td>" + i + "</td>";
		table = table + "<td>" + i + "</td>";
		table = table + "<td>" + i + "</td>";
		table = table + "<td>" + i + "</td>";
		table = table + "<td>" + i + "</td>";
		table = table + "<td>" + i + "</td>";
		table = table + "<td>" + i + "</td></tr>"; 
	}
*/
	 $('#mdt_content').html(table); 
}


function loadOSTData()
{
	var table;
	for (var i=0;i<15;i++)
	{
		table = table + "<tr> <td>" + "/dev/disk/by-path/pci-0000:00:07.1-scsi-0:0:0:0" + "</td>";
		table = table + "<td>" + "flntfs01-OST00" + i + "</td>";
		table = table + "<td>" + "OST" + "</td>";
		table = table + "<td>" + "<a href='#'>clo-indiana-h" + (49 + i) + "</a></td>";
		table = table + "<td>" + "<a href='#'>clo-indiana-h" + (49 + i) + "</a></td>";
		table = table + "<td>" + "OK" + "</td>";
		table = table + "<td>" + "<a href='#'>Format</a> | <a href='#'>Register</a> | <a href='#'>Start</a> | <a href='#'>Remove</a>" + "</td></tr>"; 
	}

	 $('#ost_content').html(table); 
}


function loadExistingMGTData()
{
	var table;
/*	
	for (var i=0;i<15;i++)
	{
		table = table + "<tr> <td>" + i + "</td>";
		table = table + "<td>" + i + "</td>";
		table = table + "<td>" + i + "</td>";
		table = table + "<td>" + i + "</td>";
		table = table + "<td>" + i + "</td>";
		table = table + "<td>" + i + "</td></tr>"; 
	}
*/
		//First row
		table = table + "<tr> <td><input type='radio'>1</input></td>";
		table = table + "<td>" + "cb-centos-6-s1" + "</td>";
		table = table + "<td>" + "cb-centos-6-s2" + "</td>";
		table = table + "<td>" + "10" + "</td>";
		table = table + "<td>" + "50" + "</td>";
		table = table + "<td>" + "350" + "</td></tr>"; 

		//Second row
		table = table + "<tr> <td><input type='radio'>2</input></td>";
		table = table + "<td>" + "cb-centos-6-s1" + "</td>";
		table = table + "<td>" + "cb-centos-6-s2" + "</td>";
		table = table + "<td>" + "10" + "</td>";
		table = table + "<td>" + "50" + "</td>";
		table = table + "<td>" + "350" + "</td></tr>"; 
		
		//Second row
		table = table + "<tr> <td><input type='radio'>3</input></td>";
		table = table + "<td>" + "cb-centos-6-s1" + "</td>";
		table = table + "<td>" + "cb-centos-6-s2" + "</td>";
		table = table + "<td>" + "10" + "</td>";
		table = table + "<td>" + "50" + "</td>";
		table = table + "<td>" + "350" + "</td></tr>"; 
		
		//Second row
		table = table + "<tr> <td><input type='radio'>4</input></td>";
		table = table + "<td>" + "cb-centos-6-s1" + "</td>";
		table = table + "<td>" + "cb-centos-6-s2" + "</td>";
		table = table + "<td>" + "10" + "</td>";
		table = table + "<td>" + "50" + "</td>";
		table = table + "<td>" + "350" + "</td></tr>"; 
		
		//Second row
		table = table + "<tr> <td><input type='radio'>5</input></td>";
		table = table + "<td>" + "cb-centos-6-s1" + "</td>";
		table = table + "<td>" + "cb-centos-6-s2" + "</td>";
		table = table + "<td>" + "10" + "</td>";
		table = table + "<td>" + "50" + "</td>";
		table = table + "<td>" + "350" + "</td></tr>"; 
		
		//Second row
		table = table + "<tr> <td><input type='radio'>6</input></td>";
		table = table + "<td>" + "cb-centos-6-s1" + "</td>";
		table = table + "<td>" + "cb-centos-6-s2" + "</td>";
		table = table + "<td>" + "10" + "</td>";
		table = table + "<td>" + "50" + "</td>";
		table = table + "<td>" + "350" + "</td></tr>"; 
		
	 $('#popup-existing-mgt_content').html(table); 
}

function loadNewMGTData()
{
	var table;
/*
	for (var i=0;i<15;i++)
	{
		table = table + "<tr> <td>" + i + "</td>";
		table = table + "<td>" + i + "</td>";
		table = table + "<td>" + i + "</td>";
		table = table + "<td>" + i + "</td>";
		table = table + "<td>" + i + "</td>";
		table = table + "<td>" + i + "</td></tr>"; 
	}
*/
		//First row
		table = table + "<tr> <td><input type='radio'>1</input></td>";
		table = table + "<td>" + "cb-centos-6-s1" + "</td>";
		table = table + "<td>" + "cb-centos-6-s2" + "</td>";
		table = table + "<td>" + "10" + "</td>";
		table = table + "<td>" + "50" + "</td>";
		table = table + "<td>" + "350" + "</td></tr>"; 

		//Second row
		table = table + "<tr> <td><input type='radio'>2</input></td>";
		table = table + "<td>" + "cb-centos-6-s1" + "</td>";
		table = table + "<td>" + "cb-centos-6-s2" + "</td>";
		table = table + "<td>" + "10" + "</td>";
		table = table + "<td>" + "50" + "</td>";
		table = table + "<td>" + "350" + "</td></tr>"; 
		
		//Second row
		table = table + "<tr> <td><input type='radio'>3</input></td>";
		table = table + "<td>" + "cb-centos-6-s1" + "</td>";
		table = table + "<td>" + "cb-centos-6-s2" + "</td>";
		table = table + "<td>" + "10" + "</td>";
		table = table + "<td>" + "50" + "</td>";
		table = table + "<td>" + "350" + "</td></tr>"; 
		
		//Second row
		table = table + "<tr> <td><input type='radio'>4</input></td>";
		table = table + "<td>" + "cb-centos-6-s1" + "</td>";
		table = table + "<td>" + "cb-centos-6-s2" + "</td>";
		table = table + "<td>" + "10" + "</td>";
		table = table + "<td>" + "50" + "</td>";
		table = table + "<td>" + "350" + "</td></tr>"; 
		
		//Second row
		table = table + "<tr> <td><input type='radio'>5</input></td>";
		table = table + "<td>" + "cb-centos-6-s1" + "</td>";
		table = table + "<td>" + "cb-centos-6-s2" + "</td>";
		table = table + "<td>" + "10" + "</td>";
		table = table + "<td>" + "50" + "</td>";
		table = table + "<td>" + "350" + "</td></tr>"; 
		
		//Second row
		table = table + "<tr> <td><input type='radio'>6</input></td>";
		table = table + "<td>" + "cb-centos-6-s1" + "</td>";
		table = table + "<td>" + "cb-centos-6-s2" + "</td>";
		table = table + "<td>" + "10" + "</td>";
		table = table + "<td>" + "50" + "</td>";
		table = table + "<td>" + "350" + "</td></tr>"; 
		
	 $('#popup-new-mgt_content').html(table); 
}


function loadNewMDTData()
{
		var table;
/*
	for (var i=0;i<15;i++)
	{
		table = table + "<tr> <td>" + i + "</td>";
		table = table + "<td>" + i + "</td>";
		table = table + "<td>" + i + "</td>";
		table = table + "<td>" + i + "</td>";
		table = table + "<td>" + i + "</td>";
		table = table + "<td>" + i + "</td></tr>"; 
	}
*/
		//First row
		table = table + "<tr> <td><input type='radio'>1</input></td>";
		table = table + "<td>" + "cb-centos-6-s1" + "</td>";
		table = table + "<td>" + "cb-centos-6-s2" + "</td>";
		table = table + "<td>" + "10" + "</td>";
		table = table + "<td>" + "50" + "</td>";
		table = table + "<td>" + "350" + "</td></tr>"; 

		//Second row
		table = table + "<tr> <td><input type='radio'>2</input></td>";
		table = table + "<td>" + "cb-centos-6-s1" + "</td>";
		table = table + "<td>" + "cb-centos-6-s2" + "</td>";
		table = table + "<td>" + "10" + "</td>";
		table = table + "<td>" + "50" + "</td>";
		table = table + "<td>" + "350" + "</td></tr>"; 
		
		//Second row
		table = table + "<tr> <td><input type='radio'>3</input></td>";
		table = table + "<td>" + "cb-centos-6-s1" + "</td>";
		table = table + "<td>" + "cb-centos-6-s2" + "</td>";
		table = table + "<td>" + "10" + "</td>";
		table = table + "<td>" + "50" + "</td>";
		table = table + "<td>" + "350" + "</td></tr>"; 
		
		//Second row
		table = table + "<tr> <td><input type='radio'>4</input></td>";
		table = table + "<td>" + "cb-centos-6-s1" + "</td>";
		table = table + "<td>" + "cb-centos-6-s2" + "</td>";
		table = table + "<td>" + "10" + "</td>";
		table = table + "<td>" + "50" + "</td>";
		table = table + "<td>" + "350" + "</td></tr>"; 
		
		//Second row
		table = table + "<tr> <td><input type='radio'>5</input></td>";
		table = table + "<td>" + "cb-centos-6-s1" + "</td>";
		table = table + "<td>" + "cb-centos-6-s2" + "</td>";
		table = table + "<td>" + "10" + "</td>";
		table = table + "<td>" + "50" + "</td>";
		table = table + "<td>" + "350" + "</td></tr>"; 
		
		//Second row
		table = table + "<tr> <td><input type='radio'>6</input></td>";
		table = table + "<td>" + "cb-centos-6-s1" + "</td>";
		table = table + "<td>" + "cb-centos-6-s2" + "</td>";
		table = table + "<td>" + "10" + "</td>";
		table = table + "<td>" + "50" + "</td>";
		table = table + "<td>" + "350" + "</td></tr>"; 
		
	 $('#popup-new-mdt_content').html(table); 
}

function loadNewOSTData()
{
		var table;

/*
	for (var i=0;i<15;i++)
	{
		table = table + "<tr> <td>" + i + "</td>";
		table = table + "<td>" + i + "</td>";
		table = table + "<td>" + i + "</td>";
		table = table + "<td>" + i + "</td>";
		table = table + "<td>" + i + "</td>";
		table = table + "<td>" + i + "</td></tr>"; 
	}
*/
		//First row
		table = table + "<tr> <td><input type='checkbox'></input></td>";
		table = table + "<td>" + "cb-centos-6-s1" + "</td>";
		table = table + "<td>" + "cb-centos-6-s2" + "</td>";
		table = table + "<td>" + "10" + "</td>";
		table = table + "<td>" + "50" + "</td>";
		table = table + "<td>" + "350" + "</td></tr>"; 

		//Second row
		table = table + "<tr> <td><input type='checkbox'></input></td>";
		table = table + "<td>" + "cb-centos-6-s1" + "</td>";
		table = table + "<td>" + "cb-centos-6-s2" + "</td>";
		table = table + "<td>" + "10" + "</td>";
		table = table + "<td>" + "50" + "</td>";
		table = table + "<td>" + "350" + "</td></tr>"; 
		
		//Second row
		table = table + "<tr> <td><input type='checkbox'></input></td>";
		table = table + "<td>" + "cb-centos-6-s1" + "</td>";
		table = table + "<td>" + "cb-centos-6-s2" + "</td>";
		table = table + "<td>" + "10" + "</td>";
		table = table + "<td>" + "50" + "</td>";
		table = table + "<td>" + "350" + "</td></tr>"; 
		
		//Second row
		table = table + "<tr> <td><input type='checkbox'></input></td>";
		table = table + "<td>" + "cb-centos-6-s1" + "</td>";
		table = table + "<td>" + "cb-centos-6-s2" + "</td>";
		table = table + "<td>" + "10" + "</td>";
		table = table + "<td>" + "50" + "</td>";
		table = table + "<td>" + "350" + "</td></tr>"; 
		
		//Second row
		table = table + "<tr> <td><input type='checkbox'></input></td>";
		table = table + "<td>" + "cb-centos-6-s1" + "</td>";
		table = table + "<td>" + "cb-centos-6-s2" + "</td>";
		table = table + "<td>" + "10" + "</td>";
		table = table + "<td>" + "50" + "</td>";
		table = table + "<td>" + "350" + "</td></tr>"; 
		
		//Second row
		table = table + "<tr> <td><input type='checkbox'></input></td>";
		table = table + "<td>" + "cb-centos-6-s1" + "</td>";
		table = table + "<td>" + "cb-centos-6-s2" + "</td>";
		table = table + "<td>" + "10" + "</td>";
		table = table + "<td>" + "50" + "</td>";
		table = table + "<td>" + "350" + "</td></tr>"; 
		
	 $('#popup-new-ost_content').html(table); 
}


function loadMGTConfiguration()
{
		var table;

/*
	for (var i=0;i<15;i++)
	{
		table = table + "<tr> <td>" + i + "</td>";
		table = table + "<td>" + i + "</td>";
		table = table + "<td>" + i + "</td>";
		table = table + "<td>" + i + "</td>";
		table = table + "<td>" + i + "</td>";
		table = table + "<td>" + i + "</td></tr>"; 
	}
*/
		//First row
		table = table + "<tr> <td>/disk/disk/by-path/pci-0000.00:71-scsi-0:00</td>";
		table = table + "<td>" + "cb-centos-6-s1" + "</td>";
		table = table + "<td>" + "cb-centos-6-s2" + "</td>";
		table = table + "<td>" + "10" + "</td>";
		table = table + "<td>" + "50" + "</td>";
		table = table + "<td>" + "350" + "</td></tr>"; 

		//Second row
		table = table + "<tr> <td>/disk/disk/by-path/pci-0000.00:71-scsi-0:00</td>";
		table = table + "<td>" + "cb-centos-6-s1" + "</td>";
		table = table + "<td>" + "cb-centos-6-s2" + "</td>";
		table = table + "<td>" + "10" + "</td>";
		table = table + "<td>" + "50" + "</td>";
		table = table + "<td>" + "350" + "</td></tr>"; 
		
		//Second row
		table = table + "<tr> <td>/disk/disk/by-path/pci-0000.00:71-scsi-0:00</td>";
		table = table + "<td>" + "cb-centos-6-s1" + "</td>";
		table = table + "<td>" + "cb-centos-6-s2" + "</td>";
		table = table + "<td>" + "10" + "</td>";
		table = table + "<td>" + "50" + "</td>";
		table = table + "<td>" + "350" + "</td></tr>"; 
		
		//Second row
		table = table + "<tr> <td>/disk/disk/by-path/pci-0000.00:71-scsi-0:00</td>";
		table = table + "<td>" + "cb-centos-6-s1" + "</td>";
		table = table + "<td>" + "cb-centos-6-s2" + "</td>";
		table = table + "<td>" + "10" + "</td>";
		table = table + "<td>" + "50" + "</td>";
		table = table + "<td>" + "350" + "</td></tr>"; 
		
		//Third row
		table = table + "<tr> <td>/disk/disk/by-path/pci-0000.00:71-scsi-0:00</td>";
		table = table + "<td>" + "cb-centos-6-s1" + "</td>";
		table = table + "<td>" + "cb-centos-6-s2" + "</td>";
		table = table + "<td>" + "10" + "</td>";
		table = table + "<td>" + "50" + "</td>";
		table = table + "<td>" + "350" + "</td></tr>"; 
		
		//Second row
		table = table + "<tr> <td>/disk/disk/by-path/pci-0000.00:71-scsi-0:00</td>";
		table = table + "<td>" + "cb-centos-6-s1" + "</td>";
		table = table + "<td>" + "cb-centos-6-s2" + "</td>";
		table = table + "<td>" + "10" + "</td>";
		table = table + "<td>" + "50" + "</td>";
		table = table + "<td>" + "350" + "</td></tr>"; 
		
	 $('#mgt_configuration_content').html(table); 
}

function loadVolumeConfiguration()
{
	var volumeTab;
	$.post("/api/getdevices/",{"hostid": ""})
	   	.success(function(data, textStatus, jqXHR) {
		   	 if(data.success)
	         {
	    	     $.each(data.response, function(resKey, resValue)
	             {
					volumeTab = volumeTab + "<tr><td>" + resValue.devicepath + "</td>"; 
					volumeTab = volumeTab + "<td>" + resValue.host+ "</td>";
					volumeTab = volumeTab + "<td>" + "<select><option value='volvo'>cb-indiana-h1</option></select>" + "</td>";
					volumeTab = volumeTab + "<td>" + "<select><option value='volvo'>cb-indiana-h1</option></select>" + "</td>";
					volumeTab = volumeTab + "<td>" + resValue.devicestatus + "</td>";
					volumeTab = volumeTab + "<td>" + resValue.devicecapacity + "</td></tr>"; 
	            });
	         }
		})
		.error(function(event) {
		//$('#outputDiv').html("Error loading list, check connection between browser and Hydra server");
		})
		.complete(function(event){  
		   $('#volume_configuration_content').html(volumeTab);
		});
	}

function loadServerConfiguration()
{
	var table;

/*
	for (var i=0;i<15;i++)
	{
		table = table + "<tr> <td>" + i + "</td>";
		table = table + "<td>" + i + "</td>";
		table = table + "<td>" + i + "</td>";
		table = table + "<td>" + i + "</td>";
		table = table + "<td>" + i + "</td>";
		table = table + "<td>" + i + "</td></tr>"; 
	}
*/
		//First row
		table = table + "<tr><td><a href='#'>cb-indiana-h1</a></td>";
		table = table + "<td>" + "<a href='#'>co-indiana-h2</a>" + "</td>";
		table = table + "<td>" + "OK" + "</td>";
		table = table + "<td>" + "<a href='#'>Stop Lnet</a> | <a href='#'>Remove</a> | <a href='#'>Unload Lnet</a> | <a href='#'>Configuration</a>" + "</td></tr>"; 

		//Second row
		table = table + "<tr><td><a href='#'>cb-indiana-h1</a></td>";
		table = table + "<td>" + "<a href='#'>co-indiana-h2</a>" + "</td>";
		table = table + "<td>" + "OK" + "</td>";
		table = table + "<td>" + "<a href='#'>Stop Lnet</a> | <a href='#'>Remove</a> | <a href='#'>Unload Lnet</a> | <a href='#'>Configuration</a>" + "</td></tr>"; 
		
		//Third row
		table = table + "<tr><td><a href='#'>cb-indiana-h1</a></td>";
		table = table + "<td>" + "<a href='#'>co-indiana-h2</a>" + "</td>";
		table = table + "<td>" + "OK" + "</td>";
		table = table + "<td>" + "<a href='#'>Stop Lnet</a> | <a href='#'>Remove</a> | <a href='#'>Unload Lnet</a> | <a href='#'>Configuration</a>" + "</td></tr>"; 
		
		//Fourth row
		table = table + "<tr><td><a href='#'>cb-indiana-h1</a></td>";
		table = table + "<td>" + "<a href='#'>co-indiana-h2</a>" + "</td>";
		table = table + "<td>" + "OK" + "</td>";
		table = table + "<td>" + "<a href='#'>Stop Lnet</a> | <a href='#'>Remove</a> | <a href='#'>Unload Lnet</a> | <a href='#'>Configuration</a>" + "</td></tr>"; 
		
		//Fifth row
		table = table + "<tr><td><a href='#'>cb-indiana-h1</a></td>";
		table = table + "<td>" + "<a href='#'>co-indiana-h2</a>" + "</td>";
		table = table + "<td>" + "OK" + "</td>";
		table = table + "<td>" + "<a href='#'>Stop Lnet</a> | <a href='#'>Remove</a> | <a href='#'>Unload Lnet</a> | <a href='#'>Configuration</a>" + "</td></tr>"; 
		
		//Sixth row
		table = table + "<tr><td><a href='#'>cb-indiana-h1</a></td>";
		table = table + "<td>" + "<a href='#'>co-indiana-h2</a>" + "</td>";
		table = table + "<td>" + "OK" + "</td>";
		table = table + "<td>" + "<a href='#'>Stop Lnet</a> | <a href='#'>Remove</a> | <a href='#'>Unload Lnet</a> | <a href='#'>Configuration</a>" + "</td></tr>"; 

	 $('#server_configuration_content').html(table); 
}