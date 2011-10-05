// JavaScript Document

function loadData()
{
		var table = "<thead>" +
 		"<tr> " +
 			" <th width='13%'>Lustre FS name</th>" +
			"<th width='12%'>MGS Name</th>" +
			"<th width='13%'>MDS Name</th>" +
			"<th width='7%'>No of OSS</th>" +
			"<th width='7%'>No of OST</th>" +
            "<th width='7%'>Used (TB)</th>" +
            "<th width='7%'>Free (TB)</th>" +
            "<th width='15%'>Action</th>" +
		"</tr>" +
	"</thead><tbody>";
	
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

	table = table + "</tbody>";
	 $('#example').html(table); 
}



function loadMgtData()
{
		var table = "<thead>" +
 		"<tr> " +
 			" <th width='15%'>Target Path</th>" +
			"<th width='12%'>Target Name</th>" +
			"<th width='7%'>Kind</th>" +
			"<th width='7%'>Server Name</th>" +
			"<th width='7%'>Fail Over</th>" +
            "<th width='5%'>Status</th>" +
            "<th width='13%'></th>" +
		"</tr>" +
	"</thead><tbody>";
	
		//First row
		table = table + "<tr> <td>" + "/dev/disk/by-path/pci-0000:00.1-scsi-0:0:0:0" + "</td>";
		table = table + "<td>" + "flntfs01-MGT0001" + "</td>";
		table = table + "<td>" + "MGT" + "</td>";
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

	table = table + "</tbody>";
	 $('#example').html(table); 
}

function loadMDTData()
{
		var table = "<thead>" +
 		"<tr> " +
 			"<th width='13%'>Target Path</th>" +
			"<th width='10%'>Target Name</th>" +
			"<th width='7%'>Kind</th>" +
			"<th width='12%'>Server Name</th>" +
			"<th width='7%'>Failover</th>" +
            "<th width='5%'>Status</th>" +
            "<th width='13%'></th>" +
		"</tr>" +
	"</thead><tbody>";
	
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
	table = table + "</tbody>";
	 $('#mdt').html(table); 
}


function loadOSTData()
{
		var table = "<thead>" +
 		"<tr> " +
 			" <th width='16%'>Target Path</th>" +
			"<th width='10%'>Target Name</th>" +
			"<th width='5%'>Kind</th>" +
			"<th width='7%'>Server Name</th>" +
			"<th width='7%'>Failover</th>" +
            "<th width='7%'>Status</th>" +
            "<th width='12%'></th>" +
		"</tr>" +
	"</thead><tbody>";
	
	
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

	table = table + "</tbody>";
	 $('#ost').html(table); 
}


function loadExistingMGTData()
{
		var table = "<thead>" +
 		"<tr> " +
 			" <th width='16%'>Select</th>" +
			"<th width='17%'>Target Path</th>" +
			"<th width='16%'>Server Name</th>" +
			"<th width='17%'>Fail Over</th>" +
			"<th width='16%'>Status</th>" +
            "<th width='17%'>Capacity (TB)</th>" +
		"</tr>" +
	"</thead><tbody>";

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
		
		table = table + "</tbody>";
	 $('#popup-existing-mgt').html(table); 
}

function loadNewMGTData()
{
		var table = "<thead>" +
 		"<tr> " +
 			" <th width='16%'>Select</th>" +
			"<th width='17%'>Target Path</th>" +
			"<th width='16%'>Server Name</th>" +
			"<th width='17%'>Fail Over</th>" +
			"<th width='16%'>Status</th>" +
            "<th width='17%'>Capacity (TB)</th>" +
		"</tr>" +
	"</thead><tbody>";

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
		
		table = table + "</tbody>";
	 $('#popup-new-mgt').html(table); 
}


function loadNewMDTData()
{
		var table = "<thead>" +
 		"<tr> " +
 			" <th width='16%'>Select</th>" +
			"<th width='17%'>Target Path</th>" +
			"<th width='16%'>Server Name</th>" +
			"<th width='17%'>Fail Over</th>" +
			"<th width='16%'>Status</th>" +
            "<th width='17%'>Capacity (TB)</th>" +
		"</tr>" +
	"</thead><tbody>";

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
		
		table = table + "</tbody>";
	 $('#popup-new-mdt').html(table); 
}

function loadNewOSTData()
{
		var table = "<thead>" +
 		"<tr> " +
 			" <th width='16%'>Select</th>" +
			"<th width='17%'>Target Path</th>" +
			"<th width='16%'>Server Name</th>" +
			"<th width='17%'>Fail Over</th>" +
			"<th width='16%'>Status</th>" +
            "<th width='17%'>Capacity (TB)</th>" +
		"</tr>" +
	"</thead><tbody>";

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
		
		table = table + "</tbody>";
	 $('#popup-new-ost').html(table); 
}


function loadMGTConfiguration()
{
		var table = "<thead>" +
 		"<tr> " +
 			"<th width='16%'>Target Path</th>" +
			"<th width='17%'>Target Name</th>" +
			"<th width='16%'>Kind</th>" +
			"<th width='17%'>Server Name</th>" +
			"<th width='16%'>Failover</th>" +
            "<th width='17%'>Action</th>" +
		"</tr>" +
	"</thead><tbody>";

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
		
		table = table + "</tbody>";
	 $('#mgt_configuration').html(table); 
}

function loadVolumeConfiguration()
{
		var table = "<thead>" +
 		"<tr> " +
 			"<th width='16%'>Target Path</th>" +
			"<th width='16%'>Server Name</th>" +
			"<th width='17%'>Failover</th>" +
			"<th width='16%'>Status</th>" +
            "<th width='17%'>Capacity</th>" +
		"</tr>" +
	"</thead><tbody>";

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
		table = table + "<td>" + "<select><option value='volvo'>cb-indiana-h1</option></select>" + "</td>";
		table = table + "<td>" + "<select><option value='volvo'>cb-indiana-h1</option></select>" + "</td>";
		table = table + "<td>" + "OK" + "</td>";
		table = table + "<td>" + "350" + "</td></tr>"; 

		//Second row
		table = table + "<tr> <td>/disk/disk/by-path/pci-0000.00:71-scsi-0:00</td>";
		table = table + "<td>" + "<select><option value='volvo'>cb-indiana-h1</option></select>" + "</td>";
		table = table + "<td>" + "<select><option value='volvo'>cb-indiana-h1</option></select>" + "</td>";
		table = table + "<td>" + "OK" + "</td>";
		table = table + "<td>" + "350" + "</td></tr>"; 
		
		//Third row
		table = table + "<tr> <td>/disk/disk/by-path/pci-0000.00:71-scsi-0:00</td>";
		table = table + "<td>" + "<select><option value='volvo'>cb-indiana-h1</option></select>" + "</td>";
		table = table + "<td>" + "<select><option value='volvo'>cb-indiana-h1</option></select>" + "</td>";
		table = table + "<td>" + "OK" + "</td>";
		table = table + "<td>" + "350" + "</td></tr>"; 
		
		//Fourth row
		table = table + "<tr> <td>/disk/disk/by-path/pci-0000.00:71-scsi-0:00</td>";
		table = table + "<td>" + "<select><option value='volvo'>cb-indiana-h1</option></select>" + "</td>";
		table = table + "<td>" + "<select><option value='volvo'>cb-indiana-h1</option></select>" + "</td>";
		table = table + "<td>" + "OK" + "</td>";
		table = table + "<td>" + "350" + "</td></tr>"; 
		
		//Fifth row
		table = table + "<tr> <td>/disk/disk/by-path/pci-0000.00:71-scsi-0:00</td>";
		table = table + "<td>" + "<select><option value='volvo'>cb-indiana-h1</option></select>" + "</td>";
		table = table + "<td>" + "<select><option value='volvo'>cb-indiana-h1</option></select>" + "</td>";
		table = table + "<td>" + "OK" + "</td>";
		table = table + "<td>" + "350" + "</td></tr>"; 
		
		//Sixth row
		table = table + "<tr> <td>/disk/disk/by-path/pci-0000.00:71-scsi-0:00</td>";
		table = table + "<td>" + "<select><option value='volvo'>cb-indiana-h1</option></select>" + "</td>";
		table = table + "<td>" + "<select><option value='volvo'>cb-indiana-h1</option></select>" + "</td>";
		table = table + "<td>" + "OK" + "</td>";
		table = table + "<td>" + "350" + "</td></tr>"; 
		
		table = table + "</tbody>";
	 $('#volume_configuration').html(table); 
}

function loadServerConfiguration()
{
		var table = "<thead>" +
 		"<tr> " +
 			"<th width='16%'>Server Name</th>" +
			"<th width='16%'>Fail Node</th>" +
			"<th width='17%'>Status</th>" +
			"<th width='16%'></th>" +
		"</tr>" +
	"</thead><tbody>";

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
		
		table = table + "</tbody>";
	 $('#server_configuration').html(table); 
}