const app=document.querySelector('#app');
const productPhoto='<img class="photo" src="../presentation/assets/cup.jpg" alt="Белая керамическая кружка">';
let method='Самовывоз', step=new URLSearchParams(location.search).get('view')==='buyer'?3:0;
const titles=['Пульт продаж','Публикация','Запись сообщества','Кружка «Мел»','Заказы','Заказ выдан','Заказ отменён'];
function button(label,to,secondary=false){return '<button class="btn '+(secondary?'back':'')+'" data-step="'+to+'">'+label+'</button>'}
function row(key,value){return '<div class="row"><span>'+key+'</span><b>'+value+'</b></div>'}
function view(){
 const product='<section class="card">'+productPhoto+'<h2>Кружка «Мел»</h2>'+row('Цена','1 200 ₽')+row('Остаток','8 шт.')+'</section>';
 const setup='<section class="card"><span class="tag">Каталог подключён</span><h2>Подготовка к продаже</h2>'+row('Фото и цена','Готово')+row('Получение','Нужна настройка')+'<p>Покупатель увидит условия до оформления заказа.</p><label>Способ получения <select id="method"><option>Самовывоз</option><option>Доставка курьером</option></select></label>'+button('Сохранить и создать запись',1)+'</section>';
 const screens=['<div class="grid">'+product+setup+'</div>',
 '<div class="grid">'+product+'<section class="card"><h2>Новая запись</h2><p>Достали из печи новую партию белых кружек. Осталось восемь штук. Прикрепляем товар, чтобы можно было заказать здесь.</p>'+row('Получение',method)+row('Прикреплённый товар','Кружка «Мел»')+button('Опубликовать',2)+'</section></div>',
 '<section class="card store"><b>Мастерская «Тёплый дом»</b><p>Достали из печи новую партию белых кружек. Осталось восемь штук.</p>'+productPhoto+button('Кружка «Мел» · 1 200 ₽',3)+'</section>',
 '<section class="card store">'+productPhoto+'<h2>Кружка «Мел»</h2><b>1 200 ₽</b><p>Белая глазурь, 300 мл. Сделана вручную в нашей мастерской.</p>'+row('Получение',method)+button('Оформить заказ',4)+'</section>',
 '<section class="card"><span class="tag">Оформлен</span><h2>Заказ № 104</h2>'+row('Товар','Кружка «Мел» × 1')+row('Сумма','1 200 ₽')+row('Получение',method)+'<p>Подтвердите выдачу после передачи кружки покупателю.</p>'+button('Подтвердить выдачу',5)+button('Отменить заказ',6,true)+'</section>',
 '<section class="card"><span class="tag">Выполнен</span><h2>Покупатель получил кружку</h2>'+row('Заказ № 104','Выдан')+row('Источник','Запись сообщества')+button('Вернуться в кабинет',0)+'</section>',
 '<section class="card"><h2>Заказ № 104 отменён</h2><p>Оформление осталось в истории. Выдачу в статистику выполненных заказов не включаем.</p>'+button('Вернуться в кабинет',0)+'</section>'];
 app.innerHTML='<div class="banner"><small>'+((step===2||step===3)?'Витрина покупателя':'Управление сообществом')+'</small><h1>'+titles[step]+'</h1>Мастерская «Тёплый дом»</div>'+screens[step];
}
app.onclick=e=>{const b=e.target.closest('[data-step]');if(!b)return;if(step===0)method=document.querySelector('#method').value;step=Number(b.dataset.step);view()};view();
