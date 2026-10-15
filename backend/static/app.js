(() => {
  const login = document.getElementById('login'), root = document.getElementById('root');
  const content = document.getElementById('content'), nav = document.getElementById('nav');
  const heading = document.getElementById('pageheading');
  const names = {resumo:'Visão geral',protocolos:'Protocolos',leis:'Legislação',fornecedores:'Fornecedores',compras:'Compras',contratos:'Contratos',bens:'Patrimônio',estoque:'Almoxarifado',auditoria:'Auditoria'};
  const forms = {
    protocolos:[['assunto','Assunto'],['requerente','Requerente'],['setor_atual','Setor inicial'],['descricao','Descrição','textarea']],
    leis:[['tipo','Tipo'],['numero','Número'],['ano','Ano','number'],['ementa','Ementa','textarea']],
    fornecedores:[['nome','Nome / Razão social'],['documento','CPF / CNPJ'],['email','E-mail','email']],
    compras:[['descricao','Descrição'],['solicitante','Setor solicitante'],['valor_estimado','Valor estimado','number'],['justificativa','Justificativa','textarea']],
    contratos:[['numero','Número do contrato'],['objeto','Objeto','textarea'],['fornecedor_id','ID do fornecedor','number'],['valor_global','Valor global','number'],['vigencia_inicio','Início da vigência','date'],['vigencia_fim','Fim da vigência','date']],
    bens:[['tombamento','Tombo'],['descricao','Descrição'],['localizacao','Localização'],['valor_aquisicao','Valor de aquisição','number']],
    estoque:[['codigo','Código'],['descricao','Descrição'],['unidade','Unidade']]
  };
  let token = '', profile = '', user = '', current = 'resumo';
  const el = (tag,cls,txt) => { const n=document.createElement(tag); if(cls)n.className=cls; if(txt!==undefined)n.textContent=String(txt); return n; };
  const format = (v) => v == null ? '—' : typeof v === 'object' ? JSON.stringify(v) : String(v);
  async function api(path,method='GET',data) {
    const res=await fetch('/api/'+path,{method,headers:{'Authorization':'Bearer '+token,...(data?{'Content-Type':'application/json'}:{})},body:data?JSON.stringify(data):undefined});
    const body=await res.json().catch(()=>({detail:'Resposta inválida'}));
    if(!res.ok)throw new Error(typeof body.detail==='string'?body.detail:JSON.stringify(body.detail||body));
    return body;
  }
  const panel = () => el('section','panel');
  const btn = (caption,fn) => {const b=el('button','primary',caption);b.onclick=fn;return b;};
  function message(target,txt){ const p=el('p','error',txt);target.append(p); }
  function showNav(){
    nav.replaceChildren();
    for(const [id,label] of Object.entries(names)){
      if(id==='auditoria' && profile!=='admin')continue;
      const b=el('button',id===current?'active':'',label);
      b.onclick=()=>render(id);nav.append(b);
    }
  }
  function table(records){
    const wrap=panel();
    if(!records.length){wrap.append(el('div','empty','Nenhum registro cadastrado.'));return wrap;}
    const keys=Object.keys(records[0]).filter(k=>!['entidade_id','senha_hash'].includes(k)).slice(0,8);
    const tbl=el('table'), thead=el('thead'), tr=el('tr');
    keys.forEach(k=>tr.append(el('th','',k.replaceAll('_',' '))));thead.append(tr);tbl.append(thead);
    const tbody=el('tbody');
    records.forEach(record=>{const row=el('tr');keys.forEach(k=>row.append(el('td','',format(record[k]))));tbody.append(row);});
    tbl.append(tbody);wrap.append(tbl);return wrap;
  }
  function createView(id){
    const host=panel(), title=el('h2','','Novo cadastro');host.append(title);
    const f=el('form'), grid=el('div','formgrid');
    for(const [key,label,type] of forms[id]){
      const field=el('label','',label);
      let input = document.createElement(type==='textarea'?'textarea':'input');
      if(type!=='textarea')input.type=type||'text';
      if(type==='number')input.step=(['valor_aquisicao','valor_estimado','valor_global'].includes(key)?'.01':'1');
      input.name=key; input.required=!['descricao','email'].includes(key);
      if(key==='unidade')input.value='un';
      field.append(input);grid.append(field);
    }
    f.append(grid);
    const submit=el('button','primary','Salvar cadastro');submit.type='submit';f.append(submit);
    f.onsubmit=async e=>{e.preventDefault();submit.disabled=true;
      const data=Object.fromEntries(new FormData(f));
      if(id==='leis')data.ano=Number(data.ano);
      if(id==='bens')data.valor_aquisicao=Number(data.valor_aquisicao);
      if(id==='protocolos'&&!data.descricao)data.descricao='';
      try{await api(id,'POST',data);await render(id)}catch(err){message(host,err.message)}finally{submit.disabled=false;}
    };
    host.append(f);return host;
  }
  async function render(id){
    current=id;heading.textContent=names[id];showNav();content.replaceChildren(el('p','small','Carregando...'));
    try{
      if(id==='resumo'){
        const values=await api('resumo');const cards=el('div','stats');
        for(const [k,v] of Object.entries(values)){const c=panel();c.append(el('div','statlabel',names[k]||k),el('div','metric',v));cards.append(c);}
        content.replaceChildren(cards);
        const note=panel();note.append(el('h2','','Ambiente demonstrativo'),el('p','small','Os registros pertencem apenas à entidade autenticada. Não utilize dados reais antes da homologação.'));
        content.append(note);
        return;
      }
      const rows=await api(id);
      const top=el('div','headrow');
      top.append(el('h2','',names[id]));
      if(forms[id]&&profile!=='leitor'){let creating=false;const add=btn('+ Novo registro',()=>{creating=!creating;const old=document.getElementById('create');if(old)old.remove();if(creating){const f=createView(id);f.id='create';top.after(f);}});top.append(add);}
      content.replaceChildren(top,table(rows));
    }catch(err){content.replaceChildren(panel());message(content.firstChild,err.message);}
  }
  document.getElementById('loginform').onsubmit=async e=>{
    e.preventDefault();const error=document.getElementById('loginerror');error.textContent='';
    try{const form=Object.fromEntries(new FormData(e.target));
      const res=await fetch('/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(form)});
      const data=await res.json();if(!res.ok)throw new Error(data.detail||'Falha no login');
      token=data.access_token;profile=data.perfil;user=data.nome;
      document.getElementById('username').textContent=data.entidade+' · '+user;
      login.hidden=true;root.hidden=false;await render('resumo');
    }catch(err){error.textContent=err.message;}
  };
  document.getElementById('logout').onclick=async()=>{
    try { if(token) await api('auth/revogar-sessoes','POST'); }
    catch (err) { console.warn('Falha ao revogar sessão remotamente'); }
    finally { token=''; profile=''; content.replaceChildren(); root.hidden=true; login.hidden=false; }
  };
})();