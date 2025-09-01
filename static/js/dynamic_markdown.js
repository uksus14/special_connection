function getColonName(el,full=false){
    const owned = ([...el.classList]).reduce((acc, cur) => acc+cur.startsWith('pill-'), 0);
    if(owned == 0) return "none";
    if(owned == 2 || full) return "both";
    return window.users.map(({pk, name}) => {
        if(el.classList.contains(`pill-${pk}`)) return name;
    }).find(name => name);
}
function coreToggle(id, full=false){
    const el = document.getElementById(`core-${id}`);
    const oldName = getColonName(el, full);
    el.classList.toggle(`pill-${window.userPK}`);
    const newName = getColonName(el, full);
    if(window.dynamicMarkdownLocal){
        editor.value = editor.value.replace(`:${oldName}-${id}`, `:${newName}-${id}`)
    }else{
        fetch(`/toggle?id=${id}`, {
            method: "POST",
            body: JSON.stringify({oldName, newName}),
            headers: { 'X-CSRFToken': window.csrf_token }
        }).then(res => res.json()).then(data => {
            if(data.changed)changed();
        })
    }
}