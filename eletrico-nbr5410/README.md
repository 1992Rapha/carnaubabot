# 🔌 Ferramenta NBR 5410 - AltoQi Elétrico

Ferramenta completa para projeto elétrico residencial conforme **NBR 5410:2008**.

## 📋 Características

✅ **18 Procedimentos do AltoQi Elétrico**
- 1. Cadastro (Base de dados)
- 2-3. Lançamentos (Lâmpadas, Tomadas)
- 4-5. Quadros e Pontos
- 7. Condutos
- 8-9. Operações (Quadros e Circuitos)
- 11-12. Fiação
- 13. Dimensionamento
- 14-15. Erros e Avisos
- 16-17. Documentação
- 18. Outros Procedimentos
- Módulo Fotovoltaico

✅ **Quadro de Cargas Completo**
- Lançamento de circuitos (Iluminação, TUG, TUE, Força, Chuveiro, Ar Condicionado)
- Cálculo automático de:
  - Corrente (I = P/V)
  - Queda de tensão (NBR 5410:6.4)
  - Seção de condutor (Tabela NBR 5410)
  - Disjuntor automático

✅ **Validações NBR 5410**
- ✓ Queda de tensão máxima 3% (circuitos terminais) / 5% (total)
- ✓ Compatibilidade corrente vs disjuntor
- ✓ Seção mínima de condutores
- ✓ Avisos de violação de normas

✅ **Funcionalidades**
- 💾 Salvar/Carregar projetos (Local Storage)
- 📥 Exportar para CSV
- 🖨️ Imprimir quadro de cargas
- 📊 Dashboard com estatísticas
- 📱 Responsivo (Mobile, Tablet, Desktop)

## 🚀 Como Usar

1. **Abra `index.html`** - Interface principal
2. **Acesse `quadro-cargas.html`** - Gerencie circuitos
3. Preencha os dados e o sistema calcula automaticamente
4. Exporte ou imprima conforme necessário

## 📊 Estrutura de Arquivos

```
eletrico-nbr5410/
├── index.html           # Interface principal
├── quadro-cargas.html   # Gerenciador de circuitos
├── styles.css           # Estilos CSS
└── app.js               # Lógica JavaScript
```

## ⚙️ Tecnologias

- HTML5
- CSS3 (Responsivo)
- JavaScript Vanilla (ES6+)
- Local Storage (Persistência)

## 📐 Padrões NBR 5410 Implementados

- **Correntes Padronizadas**: 10A, 16A, 20A, 25A, 32A, 40A, 50A, 63A, 80A, 100A
- **Seções de Condutores**: 1mm², 1.5mm², 2.5mm², 4mm², 6mm², 10mm², 16mm², 25mm², 35mm², 50mm²
- **Schemas**: F+N, F+F, 3F+N, 3F
- **Tensões**: 127V, 220V, 380V
- **Fator de Demanda**: Configurável (50-100%)

## 💾 Dados Salvos

- Projetos no navegador (Local Storage)
- Circuitos com histórico completo
- Configurações por projeto

## 📱 Compatibilidade

- ✅ Chrome/Chromium
- ✅ Firefox
- ✅ Safari
- ✅ Edge
- ✅ Mobile (iOS/Android)

## 🔒 Segurança

Todos os dados são salvos localmente no navegador. **Nenhuma informação é enviada para servidor**.

## 📖 Referências

- NBR 5410:2008 - Instalações elétricas de baixa tensão
- AltoQi Documentação Módulo Elétrico

---

**Desenvolvido por**: Raphael Carnaúba  
**Versão**: 1.0.0  
**Última atualização**: 2026-05-19
