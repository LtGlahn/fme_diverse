# FME rutine, konverter gammel vegreferanse til ny, fersk vegsystem-referanse

https://www.vegdata.no/ofte-stilte-sporsmal/hva-ma-jeg-vite-om-vegsystemreferanse/

### Hva skjer? 

Du sender ut skjema `Vegreferanse_konvertering_SKJEMA.xlsx`, får det tilbake ferdig utfylt med (delvis gyldige, delvis utdaterte) vegreferanseverdier. Angi riktig filnavn i FME workspace. _Det tryggeste er å legge til en ny _"reader"_  . Det kjappeste er å bare bytte filnavn på den XLSX-readeren som finnes fra før, men det er litt ... skjørt på XLSX-format. Selv om dine venner påstår de kun har føyd til verdien i tabellen så har den ofte klart å tukle med skjema uten å ville det._

Gi fornuftig filnavn på resultatfilene (XLSX og geopackage). Snurr film, dette tar en stund. Cirka et kvarter på 1500 rader, etter min erfaring. 

### Virkemåte

En vegreferanse var gyldig og riktig på en bestemt dato. Den datoen må vi vite. 

Når vi kjenner datoen er det en grei sak å slå opp mot Visveginfo-tjenestens [GetRoadReferenceForReference](https://visveginfo.opentns.org/help.htm#GetRoadReferenceForReference)-endepunkt med riktig `viewDate=<dato>` 

Eksempel: http://visveginfo.opentns.org/RoadInfoService/GetRoadReferenceForReference?roadReference=0400EV0000600100000&topologyLevel=Overview&ViewDate=2019-02-01

Som returnerer en XML som ser slik ut: 

```
<?xml version="1.0" encoding="ISO-8859-1"?>
<ArrayOfRoadReference xmlns:i="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://schemas.datacontract.org/2004/07/RoadInfoServiceContracts">
<RoadReference i:type="RoadPointReference">
<County>4</County>
<LaneCode>1#2#3#4</LaneCode>
<Municipality>0</Municipality>
<ReflinkOID>2282234</ReflinkOID>
<RoadCategory>E</RoadCategory>
<RoadNumber>6</RoadNumber>
<RoadNumberSegment>1</RoadNumberSegment>
<RoadStatus>V</RoadStatus>
<TextualRoadReference>0400EV0000600100000</TextualRoadReference>
<Measure>0</Measure>
<RoadNetPosition>
<SRID>25833</SRID>
<X>293433.07800293</X>
<Y>6712908.1640625</Y>
</RoadNetPosition>
<RoadNumberSegmentDistance>0</RoadNumberSegmentDistance>
<RoadnetHeading>12.412394232106777</RoadnetHeading>
</RoadReference>
</ArrayOfRoadReference>
```

Stedfesting på NVDB vegnett dreier seg om ID for veglenkesekvens (`ReflinkOID = 2282234`) og lineær(e) posisjon(er) (`Meausure = 0`) langs dem. 

Ferske vegreferanser etter nytt system er kun et HTTP-GET kall unna mot NVDB api V3: 
https://www.vegvesen.no/nvdb/api/v3/veg?veglenkesekvens=0@2282234


Og hvis du ikke har lagt om til det nye systemet så kan du iallfall erstatte dine foreldede verdier med oppdaterte verdier fra (det utgående) 532 vegreferanse-systemet. 
https://www.vegvesen.no/nvdb/api/v2/veg?veglenke=0@2282234

Det utgående systemet lever for øvrig fram til august 2021, men ikke la det være en sovepute. 

### Men workspace er mye mer komplekst enn som så? 

Korrekt, og det kunne utmerket godt vært pusset på. 

Hvis du har oppgitt fra- og til verdi så prøver vi å hente geometri for strekningen med visveginfo-funksjonen 
[GetRoadDataAlongRouteBetweenLocations](https://visveginfo.opentns.org/help.htm#GetRoadDataAlongRouteBetweenLocations)

I tillegg er det en del valideringer av inputdata og sånn. Hvis man først er dum nok til å akseptere XLSX som utvekslingsformat så må man nesten regne med en del innkommende rusk 

### Anbefalte forbedringer

Filnavn for input og resultat burde vært parameterstyrt, evt sniffet ut fra innhold i en katalog eller noe, ikke dette pirket med _"add reader"_. Resultatfil burde f.eks vært angitt automatisk ut fra filnavn på inputdata. 

Etter noen slike endringer er workspace en god kandidat for FME server, samt parallelisering. 

