const MODULES=[
['config','Configurações gerais','Tensão, condutor, isolação, queda admissível, temperatura, agrupamento e curto mínimo.'],
['cadastro','Cadastro técnico','Cargas, condutores, disjuntores, esquemas, DR, DPS e fatores.'],
['lampadas','Lâmpadas e comandos','Iluminação, interruptores, sensores, relés, retornos e comandos.'],
['tomadas','Tomadas','TUG, TUE, pontos de força, circuitos independentes e demanda.'],
['quadrosLanc','Quadros | lançamento','QD, QM, alimentador, gerador, nobreak, transformador e caixas.'],
['pontosGerais','Pontos em geral','Campainha, ventilador, alarme, carregador VE, aterramento e pontos especiais.'],
['condutosLanc','Condutos | lançamento','Eletrodutos, eletrocalhas, perfilados, conduletes e ligações entre pavimentos.'],
['quadrosOp','Quadros | operações','Hierarquia, centro de cargas, DPS, DR, disjuntores, barramentos e tensões.'],
['circuitosOp','Circuitos | operações','Criação, definição, fases, tipos de carga, prefixos, quedas e proteção.'],
['condutosOp','Condutos | operações','FCA, comprimento, seção, folga, legenda e lista de materiais.'],
['fiacaoOp','Fiação | operações','Passagem, trajeto, seção, cores, paralelos, terra e verificação de traçado.'],
['fiacaoCfg','Fiação | configurações','Seções mínimas, retorno, neutro, terra independente, cores e legenda.'],
['dimensionamento','Dimensionamento','Demanda, Ib, Ic, Iz, seção, disjuntor, DR, DPS e queda de tensão.'],
['errosDim','Erros de dimensionamento','Carga excessiva, proteção incompatível, fiação insuficiente e queda alta.'],
['avisos','Erros e avisos','Circuito indefinido, quadro sem ligação, esquema incompatível e traçado inválido.'],
['balanceamento','Balanceamento','Distribuição de cargas e correntes por fases A, B e C.'],
['detalhes','Quadros e diagramas','Quadro de cargas, unifilar, multifilar, lista de materiais e plantas.'],
['relatorios','Relatórios','Memorial, relatório de demanda, exportação CSV/JSON e impressão.']
];
const LOAD_TYPES={
iluminacao:{label:'Iluminação',demand:1,min:1.5,rcd:false},tug:{label:'TUG',demand:1,min:2.5,rcd:true},tue:{label:'TUE',demand:1,min:2.5,rcd:true},motor:{label:'Motor',demand:1,min:2.5,rcd:false},ar:{label:'Ar-condicionado',demand:1,min:2.5,rcd:false},campainha:{label:'Campainha',demand:1,min:1.5,rcd:false},carregador:{label:'Carregador VE',demand:1,min:6,rcd:true},alimentador:{label:'Alimentador',demand:1,min:10,rcd:false}
};
const SCHEMES={FN:{label:'F+N',phases:1,v:'vfn',cond:2},FF:{label:'F+F',phases:1,v:'vll',cond:2},'3F':{label:'3F',phases:3,v:'vll',cond:3},'3FN':{label:'3F+N',phases:3,v:'vll',cond:4}};
const PHASES=['A','B','C','AB','BC','CA','ABC'];
const BREAKERS=[6,10,16,20,25,32,40,50,63,70,80,100,125,150,175,200,225,250,300,350,400,500,630,800,1000,1250,1600,2000,2500,3200,4000];
const SECTIONS=[1.5,2.5,4,6,10,16,25,35,50,70,95,120,150,185,240,300];
const AMP_CU_PVC={1.5:15.5,2.5:21,4:28,6:36,10:50,16:68,25:89,35:110,50:134,70:171,95:207,120:239,150:275,185:314,240:370,300:426};
const AMP_CU_XLPE={1.5:19,2.5:26,4:35,6:45,10:61,16:81,25:106,35:131,50:158,70:200,95:241,120:278,150:318,185:362,240:424,300:486};
const AMP_AL_PVC={16:53,25:70,35:86,50:104,70:133,95:161,120:186,150:214,185:245,240:286,300:328};
const AMP_AL_XLPE={16:64,25:84,35:103,50:125,70:158,95:191,120:220,150:253,185:288,240:338,300:387};
const CONDUITS=[['DN20 / 1/2\"',113],['DN25 / 3/4\"',201],['DN32 / 1\"',346],['DN40 / 1.1/4\"',598],['DN50 / 1.1/2\"',881],['DN60 / 2\"',1400],['DN75 / 2.1/2\"',2290],['DN85 / 3\"',3130],['DN110 / 4\"',5540]];
const DEFAULT_CIRCUITS=[
{id:'C1',desc:'Iluminação social',type:'iluminacao',scheme:'FN',power:800,qty:1,len:22,pf:.92,df:1,phase:'A'},
{id:'C2',desc:'TUG quartos/sala',type:'tug',scheme:'FN',power:1600,qty:1,len:28,pf:.92,df:1,phase:'B'},
{id:'C3',desc:'TUG cozinha/serviço',type:'tug',scheme:'FN',power:2200,qty:1,len:32,pf:.92,df:1,phase:'C'},
{id:'C4',desc:'Chuveiro elétrico',type:'tue',scheme:'FF',power:5500,qty:1,len:18,pf:1,df:1,phase:'AB'},
{id:'C5',desc:'Ar-condicionado',type:'ar',scheme:'FF',power:1800,qty:1,len:24,pf:.85,df:1,phase:'BC'}
];
